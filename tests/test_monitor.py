from datetime import datetime, timedelta

import pytest

import alerts
import config
import db
import monitor
from platforms import LiveStatus

START = datetime(2026, 11, 2, 20, 0)  # a Monday
END = START + timedelta(hours=2)


@pytest.fixture
def conn(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    monkeypatch.setattr(config, "DATABASE", path)
    monkeypatch.setattr(alerts, "send", lambda text: None)
    db.init(path)
    c = db.connect(path)
    c.execute(
        "INSERT INTO streamers (id, name, platform, handle, checkin_token) "
        "VALUES (1, 'Amy', 'tiktok', '@amy', 'tok')"
    )
    c.execute(
        "INSERT INTO shifts (id, streamer_id, start_at, end_at) VALUES (1, 1, ?, ?)",
        (db.iso(START), db.iso(END)),
    )
    yield c
    c.close()


def run(conn, timeline):
    """timeline: list of (minutes after start, is_live)."""
    for minute, live in timeline:
        monitor.tick(conn, now=START + timedelta(minutes=minute),
                     checker=lambda s, live=live: LiveStatus(live, viewers=100 if live else None))


def shift(conn):
    return conn.execute("SELECT * FROM shifts WHERE id = 1").fetchone()


def alert_kinds(conn):
    return [r["kind"] for r in conn.execute("SELECT kind FROM alerts ORDER BY id")]


def test_perfect_shift(conn):
    run(conn, [(m, True) for m in range(0, 120, 2)] + [(121, False)])
    s = shift(conn)
    assert s["status"] == "completed"
    assert s["flags"] == ""
    assert s["live_seconds"] == 118 * 60
    assert s["peak_viewers"] == 100
    assert alert_kinds(conn) == []


def test_late_start_then_live(conn):
    run(conn, [(0, False), (4, False), (8, False), (12, True), (14, True)])
    s = shift(conn)
    assert s["status"] == "live"
    assert "late" in s["flags"]
    assert alert_kinds(conn) == ["late", "started_late"]


def test_no_show_and_missed(conn):
    run(conn, [(m, False) for m in range(0, 120, 10)] + [(125, False)])
    assert shift(conn)["status"] == "missed"
    assert alert_kinds(conn) == ["late", "no_show", "missed"]


def test_drop_mid_stream_and_recover(conn):
    run(conn, [(0, True), (2, True), (4, False), (6, False), (8, False), (10, True)])
    s = shift(conn)
    assert s["status"] == "live"
    assert s["drops"] == 1
    assert alert_kinds(conn) == ["dropped_1", "back_live_1"]


def test_single_offline_blip_is_not_a_drop(conn):
    run(conn, [(0, True), (2, False), (4, True)])
    assert shift(conn)["drops"] == 0
    assert alert_kinds(conn) == []


def test_ended_early(conn):
    run(conn, [(m, True) for m in range(0, 90, 2)] + [(m, False) for m in range(90, 120, 2)] + [(121, False)])
    s = shift(conn)
    assert s["status"] == "completed"
    assert "ended_early" in s["flags"]
    assert "ended_early" in alert_kinds(conn)


def test_unknown_checks_warn_but_do_not_count_offline(conn):
    for minute in (0, 2, 4):
        monitor.tick(conn, now=START + timedelta(minutes=minute),
                     checker=lambda s: LiveStatus(None, detail="blocked"))
    assert alert_kinds(conn) == ["check_failing"]


def test_weekly_slot_expansion_and_overnight(conn):
    conn.execute(
        "INSERT INTO weekly_slots (streamer_id, weekday, start_time, end_time) VALUES (1, 0, '22:00', '02:00')"
    )
    monitor.expand_schedule(conn, today=START, days=8)
    monitor.expand_schedule(conn, today=START, days=8)  # idempotent
    rows = conn.execute("SELECT * FROM shifts WHERE slot_id IS NOT NULL ORDER BY start_at").fetchall()
    assert [r["start_at"] for r in rows] == ["2026-11-02T22:00:00", "2026-11-09T22:00:00"]
    assert rows[0]["end_at"] == "2026-11-03T02:00:00"
