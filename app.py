"""Web UI: timetable, live dashboard, alerts, reports and streamer check-in pages."""
import csv
import io
import logging
import os
from datetime import datetime, timedelta

from flask import (
    Flask, Response, abort, flash, g, redirect, render_template, request, url_for,
)

import config
import db
import monitor
import platforms

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STATUS_LABELS = {
    "upcoming": "Upcoming", "waiting": "Starting", "live": "Live", "late": "Late",
    "no_show": "No show", "dropped": "Offline!", "completed": "Done",
    "missed": "Missed", "unchecked": "Not checked", "cancelled": "Cancelled",
}

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.jinja_env.globals.update(WEEKDAYS=WEEKDAYS, STATUS_LABELS=STATUS_LABELS, config=config)


def conn():
    if "conn" not in g:
        g.conn = db.connect()
    return g.conn


@app.teardown_appcontext
def close_conn(_exc):
    c = g.pop("conn", None)
    if c is not None:
        c.commit()
        c.close()


@app.before_request
def require_login():
    if not config.ADMIN_PASSWORD or request.endpoint in ("checkin", "checkin_action", "static"):
        return None
    auth = request.authorization
    if auth and auth.password == config.ADMIN_PASSWORD:
        return None
    return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="Time Planet"'})


@app.template_filter("hm")
def hm(value):
    return db.parse(value).strftime("%H:%M") if value else "—"


@app.template_filter("dayname")
def dayname(value):
    return db.parse(value).strftime("%a %d %b")


@app.template_filter("duration")
def duration(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def shifts_between(start, end):
    return conn().execute(
        "SELECT sh.*, s.name, s.platform, s.handle FROM shifts sh "
        "JOIN streamers s ON s.id = sh.streamer_id "
        "WHERE sh.start_at < ? AND sh.end_at > ? ORDER BY sh.start_at, s.name",
        (db.iso(end), db.iso(start)),
    ).fetchall()


# ---------------------------------------------------------------- dashboard
@app.route("/")
def dashboard():
    now = db.now()
    day = request.args.get("day")
    day_start = datetime.fromisoformat(day) if day else now.replace(hour=0, minute=0, second=0)
    shifts = shifts_between(day_start, day_start + timedelta(days=1))
    open_alerts = conn().execute(
        "SELECT a.*, s.name FROM alerts a LEFT JOIN shifts sh ON sh.id = a.shift_id "
        "LEFT JOIN streamers s ON s.id = sh.streamer_id "
        "WHERE a.acknowledged = 0 ORDER BY a.id DESC LIMIT 50"
    ).fetchall()
    counts = {}
    for sh in shifts:
        counts[sh["status"]] = counts.get(sh["status"], 0) + 1
    return render_template(
        "dashboard.html", shifts=shifts, alerts=open_alerts, counts=counts, now=now,
        day=day_start, prev_day=(day_start - timedelta(days=1)).date().isoformat(),
        next_day=(day_start + timedelta(days=1)).date().isoformat(),
    )


@app.post("/alerts/<int:alert_id>/ack")
def ack_alert(alert_id):
    conn().execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/alerts/ack-all")
def ack_all():
    conn().execute("UPDATE alerts SET acknowledged = 1 WHERE acknowledged = 0")
    return redirect(url_for("dashboard"))


@app.post("/check-now")
def check_now():
    monitor.tick(conn())
    flash("Checked all running shifts.")
    return redirect(url_for("dashboard"))


@app.route("/shift/<int:shift_id>")
def shift_detail(shift_id):
    shift = conn().execute(
        "SELECT sh.*, s.name, s.platform, s.handle FROM shifts sh "
        "JOIN streamers s ON s.id = sh.streamer_id WHERE sh.id = ?", (shift_id,)
    ).fetchone() or abort(404)
    checks = conn().execute(
        "SELECT * FROM checks WHERE shift_id = ? ORDER BY id", (shift_id,)
    ).fetchall()
    shift_alerts = conn().execute(
        "SELECT * FROM alerts WHERE shift_id = ? ORDER BY id", (shift_id,)
    ).fetchall()
    return render_template("shift.html", shift=shift, checks=checks, alerts=shift_alerts)


# ---------------------------------------------------------------- streamers
@app.route("/streamers", methods=["GET", "POST"])
def streamers():
    if request.method == "POST":
        f = request.form
        if not f.get("name") or f.get("platform") not in platforms.PLATFORMS:
            flash("Name and a valid platform are required.", "error")
        else:
            conn().execute(
                "INSERT INTO streamers (name, platform, handle, contact, checkin_token) "
                "VALUES (?, ?, ?, ?, ?)",
                (f["name"].strip(), f["platform"], f.get("handle", "").strip(),
                 f.get("contact", "").strip(), db.new_token()),
            )
            flash(f"Added {f['name']}.")
        return redirect(url_for("streamers"))
    rows = conn().execute("SELECT * FROM streamers ORDER BY active DESC, name").fetchall()
    return render_template("streamers.html", streamers=rows, platforms=platforms.PLATFORMS)


@app.post("/streamers/<int:sid>/edit")
def edit_streamer(sid):
    f = request.form
    conn().execute(
        "UPDATE streamers SET name = ?, platform = ?, handle = ?, contact = ? WHERE id = ?",
        (f["name"].strip(), f["platform"], f.get("handle", "").strip(),
         f.get("contact", "").strip(), sid),
    )
    flash("Saved.")
    return redirect(url_for("streamers"))


@app.post("/streamers/<int:sid>/toggle")
def toggle_streamer(sid):
    conn().execute("UPDATE streamers SET active = 1 - active WHERE id = ?", (sid,))
    conn().execute(
        "UPDATE shifts SET status = 'cancelled' WHERE streamer_id = ? AND status = 'upcoming' "
        "AND (SELECT active FROM streamers WHERE id = ?) = 0", (sid, sid),
    )
    return redirect(url_for("streamers"))


@app.post("/streamers/<int:sid>/test")
def test_streamer(sid):
    s = conn().execute("SELECT * FROM streamers WHERE id = ?", (sid,)).fetchone() or abort(404)
    result = platforms.check(s)
    state = {True: "LIVE", False: "offline", None: "could not tell"}[result.is_live]
    flash(f"{s['name']}: {state}. {result.detail}"
          + (f" ({result.viewers} viewers)" if result.viewers is not None else ""))
    return redirect(url_for("streamers"))


# ---------------------------------------------------------------- schedule
def _overlaps(streamer_id, start, end, ignore_slot=None):
    """Return clashing shifts for the same streamer."""
    return conn().execute(
        "SELECT * FROM shifts WHERE streamer_id = ? AND status != 'cancelled' "
        "AND start_at < ? AND end_at > ? AND (slot_id IS NULL OR slot_id != ?)",
        (streamer_id, db.iso(end), db.iso(start), ignore_slot or -1),
    ).fetchall()


@app.route("/schedule")
def schedule():
    slots = conn().execute(
        "SELECT ws.*, s.name, s.platform FROM weekly_slots ws "
        "JOIN streamers s ON s.id = ws.streamer_id ORDER BY ws.weekday, ws.start_time"
    ).fetchall()
    by_day = {i: [s for s in slots if s["weekday"] == i] for i in range(7)}
    now = db.now()
    upcoming = shifts_between(now, now + timedelta(days=7))
    active = conn().execute("SELECT * FROM streamers WHERE active = 1 ORDER BY name").fetchall()
    return render_template(
        "schedule.html", by_day=by_day, upcoming=upcoming, streamers=active,
        today=now.date().isoformat(),
    )


@app.post("/schedule/slots")
def add_slot():
    f = request.form
    days = [int(d) for d in f.getlist("weekday")]
    if not days or not f.get("start_time") or not f.get("end_time"):
        flash("Pick at least one day and a start/end time.", "error")
        return redirect(url_for("schedule"))
    for d in days:
        conn().execute(
            "INSERT INTO weekly_slots (streamer_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
            (int(f["streamer_id"]), d, f["start_time"], f["end_time"]),
        )
    monitor.expand_schedule(conn())
    clashes = conn().execute(
        "SELECT COUNT(*) FROM shifts a JOIN shifts b ON a.streamer_id = b.streamer_id "
        "AND a.id < b.id AND a.start_at < b.end_at AND a.end_at > b.start_at "
        "WHERE a.streamer_id = ? AND a.status != 'cancelled' AND b.status != 'cancelled'",
        (int(f["streamer_id"]),),
    ).fetchone()[0]
    flash("Weekly slot added." + (f" Warning: {clashes} overlapping shift(s) for this streamer." if clashes else ""))
    return redirect(url_for("schedule"))


@app.post("/schedule/slots/<int:slot_id>/delete")
def delete_slot(slot_id):
    conn().execute(
        "DELETE FROM shifts WHERE slot_id = ? AND status = 'upcoming'", (slot_id,)
    )
    conn().execute("DELETE FROM weekly_slots WHERE id = ?", (slot_id,))
    flash("Weekly slot removed (future shifts deleted).")
    return redirect(url_for("schedule"))


@app.post("/schedule/shifts")
def add_shift():
    f = request.form
    start = datetime.fromisoformat(f"{f['date']}T{f['start_time']}")
    end = datetime.fromisoformat(f"{f['date']}T{f['end_time']}")
    if end <= start:
        end += timedelta(days=1)
    sid = int(f["streamer_id"])
    clashes = _overlaps(sid, start, end)
    conn().execute(
        "INSERT OR IGNORE INTO shifts (streamer_id, start_at, end_at) VALUES (?, ?, ?)",
        (sid, db.iso(start), db.iso(end)),
    )
    flash("One-off shift added." + (" Warning: it overlaps another shift." if clashes else ""))
    return redirect(url_for("schedule"))


@app.post("/shifts/<int:shift_id>/cancel")
def cancel_shift(shift_id):
    conn().execute(
        "UPDATE shifts SET status = 'cancelled' WHERE id = ? AND status = 'upcoming'", (shift_id,)
    )
    flash("Shift cancelled.")
    return redirect(request.referrer or url_for("schedule"))


# ---------------------------------------------------------------- reports
def build_report(start, end):
    rows = conn().execute(
        "SELECT sh.*, s.name FROM shifts sh JOIN streamers s ON s.id = sh.streamer_id "
        "WHERE sh.start_at >= ? AND sh.start_at < ? AND sh.status NOT IN ('cancelled', 'upcoming', 'unchecked')",
        (db.iso(start), db.iso(end)),
    ).fetchall()
    report = {}
    for sh in rows:
        r = report.setdefault(sh["name"], dict(
            name=sh["name"], shifts=0, on_time=0, late=0, missed=0, drops=0,
            ended_early=0, scheduled=0, live=0,
        ))
        flags = sh["flags"].split(",")
        r["shifts"] += 1
        r["scheduled"] += (db.parse(sh["end_at"]) - db.parse(sh["start_at"])).total_seconds()
        r["live"] += sh["live_seconds"]
        r["drops"] += sh["drops"]
        r["ended_early"] += "ended_early" in flags
        if sh["status"] in ("missed", "no_show"):
            r["missed"] += 1
        elif "late" in flags or sh["status"] == "late":
            r["late"] += 1
        elif sh["first_live_at"]:
            r["on_time"] += 1
    for r in report.values():
        r["attendance"] = round(100 * r["live"] / r["scheduled"]) if r["scheduled"] else 0
        r["punctuality"] = round(100 * r["on_time"] / r["shifts"]) if r["shifts"] else 0
    return sorted(report.values(), key=lambda r: r["attendance"])


@app.route("/report")
def report():
    today = db.now().date()
    start = datetime.fromisoformat(request.args.get("from") or (today - timedelta(days=6)).isoformat())
    end = datetime.fromisoformat(request.args.get("to") or today.isoformat()) + timedelta(days=1)
    rows = build_report(start, end)
    if request.args.get("format") == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Streamer", "Shifts", "On time", "Late", "Missed", "Went offline",
                         "Ended early", "Scheduled hours", "Live hours", "Attendance %", "Punctuality %"])
        for r in rows:
            writer.writerow([r["name"], r["shifts"], r["on_time"], r["late"], r["missed"], r["drops"],
                             r["ended_early"], round(r["scheduled"] / 3600, 1),
                             round(r["live"] / 3600, 1), r["attendance"], r["punctuality"]])
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=streamer-report.csv"})
    return render_template("report.html", rows=rows, start=start.date().isoformat(),
                           end=(end - timedelta(days=1)).date().isoformat())


# ---------------------------------------------------------------- streamer check-in (no login)
def _streamer_by_token(token):
    return conn().execute(
        "SELECT * FROM streamers WHERE checkin_token = ?", (token,)
    ).fetchone() or abort(404)


@app.route("/c/<token>")
def checkin(token):
    s = _streamer_by_token(token)
    now = db.now()
    my_shifts = conn().execute(
        "SELECT * FROM shifts WHERE streamer_id = ? AND end_at > ? AND status != 'cancelled' "
        "ORDER BY start_at LIMIT 14", (s["id"], db.iso(now))
    ).fetchall()
    until = db.parse(s["manual_live_until"])
    return render_template("checkin.html", s=s, shifts=my_shifts, now=now,
                           manual_live=bool(until and until >= now))


@app.post("/c/<token>")
def checkin_action(token):
    s = _streamer_by_token(token)
    now = db.now()
    if request.form.get("action") == "start":
        current = conn().execute(
            "SELECT end_at FROM shifts WHERE streamer_id = ? AND start_at <= ? AND end_at > ? "
            "AND status != 'cancelled' ORDER BY end_at DESC LIMIT 1",
            (s["id"], db.iso(now + timedelta(minutes=30)), db.iso(now)),
        ).fetchone()
        until = db.parse(current["end_at"]) if current else now + timedelta(minutes=config.MANUAL_HEARTBEAT_MINUTES)
        conn().execute("UPDATE streamers SET manual_live_until = ? WHERE id = ?", (db.iso(until), s["id"]))
    else:
        conn().execute("UPDATE streamers SET manual_live_until = NULL WHERE id = ?", (s["id"],))
    return redirect(url_for("checkin", token=token))


def create_app(start_monitor=True):
    db.init()
    if start_monitor:
        monitor.start_background()
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    create_app(start_monitor=os.environ.get("TP_DISABLE_MONITOR") != "1")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
