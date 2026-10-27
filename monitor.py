"""The watchdog: expands the timetable and checks every running shift.

Shift lifecycle
    upcoming -> waiting (start, within grace) -> live
             -> late (past grace, not live)  -> live (flagged 'late')
             -> no_show (past no-show limit) -> live (flagged 'late')
    live -> dropped (offline N checks in a row) -> live again
    end of shift -> completed (flags: late, ended_early) | missed | unchecked
"""
import logging
import threading
import time
from datetime import datetime, timedelta

import alerts
import config
import db
import platforms

log = logging.getLogger("timeplanet.monitor")
FINAL = ("completed", "missed", "unchecked", "cancelled")


def expand_schedule(conn, today=None, days=None):
    """Create concrete shifts from weekly slots for the coming days."""
    today = (today or db.now()).date()
    days = config.SCHEDULE_DAYS_AHEAD if days is None else days
    slots = conn.execute(
        "SELECT ws.* FROM weekly_slots ws JOIN streamers s ON s.id = ws.streamer_id "
        "WHERE s.active = 1"
    ).fetchall()
    for offset in range(days):
        day = today + timedelta(days=offset)
        for slot in slots:
            if slot["weekday"] != day.weekday():
                continue
            start = datetime.combine(day, datetime.strptime(slot["start_time"], "%H:%M").time())
            end = datetime.combine(day, datetime.strptime(slot["end_time"], "%H:%M").time())
            if end <= start:
                end += timedelta(days=1)  # overnight shift
            conn.execute(
                "INSERT OR IGNORE INTO shifts (streamer_id, slot_id, start_at, end_at) "
                "VALUES (?, ?, ?, ?)",
                (slot["streamer_id"], slot["id"], db.iso(start), db.iso(end)),
            )


def _add_flag(flags, flag):
    items = [f for f in flags.split(",") if f]
    if flag not in items:
        items.append(flag)
    return ",".join(items)


def _hm(dt):
    return dt.strftime("%H:%M")


def apply_status(conn, shift, streamer, status, now):
    """Update one in-progress shift from a fresh LiveStatus. Returns new status."""
    start, end = db.parse(shift["start_at"]), db.parse(shift["end_at"])
    name = streamer["name"]
    window = f"{_hm(start)}-{_hm(end)}"
    fields = {"last_checked_at": db.iso(now)}
    state = shift["status"]

    conn.execute(
        "INSERT INTO checks (shift_id, checked_at, is_live, viewers, detail) VALUES (?, ?, ?, ?, ?)",
        (shift["id"], db.iso(now),
         None if status.is_live is None else int(status.is_live), status.viewers, status.detail),
    )

    if status.is_live is None:
        # Unknown: keep the current state, but do not leave the manager blind.
        streak = conn.execute(
            "SELECT COUNT(*) FROM (SELECT is_live FROM checks WHERE shift_id = ? "
            "ORDER BY id DESC LIMIT 3) WHERE is_live IS NULL", (shift["id"],)
        ).fetchone()[0]
        if streak >= 3:
            alerts.raise_alert(
                conn, shift["id"], "check_failing", "warning",
                f"Cannot verify {name} ({streamer['platform']}) — {status.detail}. Please check manually.",
            )
    elif status.is_live:
        last = db.parse(shift["last_checked_at"])
        if shift["first_live_at"] is None:
            fields["first_live_at"] = db.iso(now)
            late_by = int((now - start).total_seconds() // 60)
            if late_by > config.GRACE_MINUTES:
                fields["flags"] = _add_flag(shift["flags"], "late")
                alerts.raise_alert(
                    conn, shift["id"], "started_late", "info",
                    f"{name} went live {late_by} min late (shift {window}).",
                )
        elif last and shift["last_live_at"] == shift["last_checked_at"]:
            # previous check was live too: count the time between them (capped)
            gap = min((now - last).total_seconds(), config.CHECK_INTERVAL_SECONDS * 2)
            fields["live_seconds"] = shift["live_seconds"] + int(gap)
        if state == "dropped":
            alerts.raise_alert(
                conn, shift["id"], f"back_live_{shift['drops']}", "info",
                f"{name} is back live.",
            )
        fields.update(last_live_at=db.iso(now), offline_streak=0)
        if status.viewers is not None:
            fields["peak_viewers"] = max(shift["peak_viewers"] or 0, status.viewers)
        state = "live"
    else:
        minutes_in = (now - start).total_seconds() / 60
        if shift["first_live_at"] is None:
            if minutes_in >= config.NO_SHOW_MINUTES:
                state = "no_show"
                alerts.raise_alert(
                    conn, shift["id"], "no_show", "critical",
                    f"{name} is still NOT live {int(minutes_in)} min into shift {window}.",
                )
            elif minutes_in > config.GRACE_MINUTES:
                state = "late"
                alerts.raise_alert(
                    conn, shift["id"], "late", "warning",
                    f"{name} has not started live yet (shift {window}).",
                )
            else:
                state = "waiting"
        else:
            streak = shift["offline_streak"] + 1
            fields["offline_streak"] = streak
            if streak >= config.DROP_CHECKS and state != "dropped":
                fields["drops"] = shift["drops"] + 1
                state = "dropped"
                alerts.raise_alert(
                    conn, shift["id"], f"dropped_{fields['drops']}", "critical",
                    f"{name} went OFFLINE during shift {window} (last seen live {_hm(db.parse(shift['last_live_at']))}).",
                )

    fields["status"] = state
    _update(conn, shift["id"], fields)
    return state


def finalize(conn, shift, streamer):
    """Close a shift whose end time has passed."""
    start, end = db.parse(shift["start_at"]), db.parse(shift["end_at"])
    window = f"{start:%a %d %b} {_hm(start)}-{_hm(end)}"
    fields = {}
    if shift["last_checked_at"] is None:
        fields["status"] = "unchecked"
    elif shift["first_live_at"] is None:
        fields["status"] = "missed"
        alerts.raise_alert(
            conn, shift["id"], "missed", "critical",
            f"{streamer['name']} MISSED the whole shift {window}.",
        )
    else:
        fields["status"] = "completed"
        last_live = db.parse(shift["last_live_at"])
        if last_live < end - timedelta(minutes=config.EARLY_END_MINUTES):
            fields["flags"] = _add_flag(shift["flags"], "ended_early")
            alerts.raise_alert(
                conn, shift["id"], "ended_early", "warning",
                f"{streamer['name']} ended {int((end - last_live).total_seconds() // 60)} min early "
                f"(shift {window}, last live {_hm(last_live)}).",
            )
    _update(conn, shift["id"], fields)


def _update(conn, shift_id, fields):
    if fields:
        cols = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE shifts SET {cols} WHERE id = ?", (*fields.values(), shift_id))


def tick(conn, now=None, checker=platforms.check):
    """One monitoring pass. `checker` is injectable for tests."""
    now = now or db.now()
    expand_schedule(conn, today=now)
    rows = conn.execute(
        "SELECT sh.*, s.name, s.platform, s.handle, s.manual_live_until "
        "FROM shifts sh JOIN streamers s ON s.id = sh.streamer_id "
        f"WHERE sh.status NOT IN ({','.join('?' * len(FINAL))}) AND sh.start_at <= ?",
        (*FINAL, db.iso(now)),
    ).fetchall()
    cache = {}
    for shift in rows:
        if db.parse(shift["end_at"]) <= now:
            finalize(conn, shift, shift)
            continue
        key = shift["streamer_id"]
        if key not in cache:
            cache[key] = checker(shift)
        apply_status(conn, shift, shift, cache[key], now)
    conn.commit()


def run_forever(stop_event=None):
    stop_event = stop_event or threading.Event()
    log.info("monitor started, checking every %ss", config.CHECK_INTERVAL_SECONDS)
    while not stop_event.is_set():
        try:
            with db.session() as conn:
                tick(conn)
        except Exception:
            log.exception("monitor tick failed")
        stop_event.wait(config.CHECK_INTERVAL_SECONDS)


def start_background():
    thread = threading.Thread(target=run_forever, name="monitor", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    db.init()
    run_forever()
