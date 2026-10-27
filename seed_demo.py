"""Fill a database with sample streamers and a week of timetable, to try the UI."""
from datetime import timedelta

import db
import monitor
from platforms import LiveStatus

db.init()
with db.session() as conn:
    people = [("Amy", "tiktok", "@amy.live"), ("Ben", "youtube", "@benplays"),
              ("Cara", "twitch", "cara_tv"), ("Dan", "manual", "")]
    for name, platform, handle in people:
        conn.execute("INSERT INTO streamers (name, platform, handle, checkin_token) VALUES (?, ?, ?, ?)",
                     (name, platform, handle, db.new_token()))
    now = db.now().replace(minute=0, second=0)
    for sid in range(1, 5):
        for wd in range(7):
            start = (now - timedelta(hours=3) + timedelta(hours=sid - 1)).strftime("%H:%M")
            end = (now - timedelta(hours=1) + timedelta(hours=sid - 1)).strftime("%H:%M")
            conn.execute("INSERT INTO weekly_slots (streamer_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
                         (sid, wd, start, end))
    monitor.expand_schedule(conn, today=now, days=14)
    # simulate the past few hours: Amy perfect, Ben late then drops, Cara no-show, Dan starting
    behaviour = {1: lambda m: True, 2: lambda m: 15 < m < 70 or m > 80, 3: lambda m: False, 4: lambda m: m > 3}
    t = now - timedelta(hours=3)
    while t <= db.now():
        minute = lambda sid: (t - (now - timedelta(hours=3) + timedelta(hours=sid - 1))).total_seconds() / 60
        monitor.tick(conn, now=t, checker=lambda s: LiveStatus(behaviour[s["streamer_id"]](minute(s["streamer_id"])), 250))
        t += timedelta(minutes=2)
print("Demo data ready. Run: python app.py")
