"""SQLite storage. Times are stored as naive ISO strings in config.TIMEZONE."""
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS streamers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,          -- tiktok | youtube | twitch | manual
    handle TEXT NOT NULL DEFAULT '', -- @username / channel id / login
    contact TEXT NOT NULL DEFAULT '',-- phone / telegram, for your reference
    checkin_token TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    manual_live_until TEXT           -- manual platform: heartbeat expiry
);

-- Weekly repeating timetable; expanded into concrete shifts.
CREATE TABLE IF NOT EXISTS weekly_slots (
    id INTEGER PRIMARY KEY,
    streamer_id INTEGER NOT NULL REFERENCES streamers(id) ON DELETE CASCADE,
    weekday INTEGER NOT NULL,        -- 0 = Monday
    start_time TEXT NOT NULL,        -- HH:MM
    end_time TEXT NOT NULL           -- HH:MM (earlier than start = next day)
);

CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY,
    streamer_id INTEGER NOT NULL REFERENCES streamers(id) ON DELETE CASCADE,
    slot_id INTEGER REFERENCES weekly_slots(id) ON DELETE SET NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'upcoming',
    first_live_at TEXT,
    last_live_at TEXT,
    live_seconds INTEGER NOT NULL DEFAULT 0,
    offline_streak INTEGER NOT NULL DEFAULT 0,
    drops INTEGER NOT NULL DEFAULT 0,
    peak_viewers INTEGER,
    last_checked_at TEXT,
    flags TEXT NOT NULL DEFAULT '',  -- comma list: late, ended_early
    UNIQUE (streamer_id, start_at)
);

CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    checked_at TEXT NOT NULL,
    is_live INTEGER,
    viewers INTEGER,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    shift_id INTEGER REFERENCES shifts(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,          -- info | warning | critical
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_shifts_time ON shifts(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_checks_shift ON checks(shift_id);
"""


def now():
    """Current local time (naive, in config.TIMEZONE), second precision."""
    return datetime.now(config.TIMEZONE).replace(tzinfo=None, microsecond=0)


def iso(dt):
    return dt.isoformat(timespec="seconds") if dt else None


def parse(value):
    return datetime.fromisoformat(value) if value else None


def connect(path=None):
    conn = sqlite3.connect(path or config.DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def session(path=None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init(path=None):
    with session(path) as conn:
        conn.executescript(SCHEMA)


def new_token():
    return secrets.token_urlsafe(12)
