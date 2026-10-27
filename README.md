# 🪐 Time Planet — Live Streamer Timetable & Monitor

Plan your live streamers' timetable, and let the system watch the streams for you.
You only get a message when something is wrong. No more staring at screens.

## The flow

```
 1. ADD STREAMERS        2. BUILD TIMETABLE         3. AUTO-MONITOR (every 2 min)       4. YOU
 name + platform   ──►   weekly slots +       ──►   is the channel live right now?  ──► get Telegram/Discord
 + channel handle        one-off shifts             └ records live time & viewers        alerts ONLY when needed
                                                                                          + weekly report
```

What the monitor catches, per shift:

| Situation | When | Alert |
|---|---|---|
| Not live yet | 5 min after start | ⚠️ warning |
| **No show** | 20 min after start, still not live | 🚨 urgent |
| Went live late | the moment they start | ℹ️ info (and flagged `late` in report) |
| **Went offline mid-stream** | offline 2 checks in a row (~4 min) | 🚨 urgent |
| Back live | after a drop | ℹ️ info |
| Ended early | stopped >10 min before shift end | ⚠️ warning |
| **Missed whole shift** | shift ended, never live | 🚨 urgent |
| Can't verify | platform check failed 3× | ⚠️ "check manually" |

One short offline blip is ignored, so you are not spammed by a network hiccup.
All the minute values can be changed in `.env`.

## Pages

- **Dashboard** – today's shifts with live status, live time, peak viewers, and a "Needs attention" list. Refreshes every minute.
- **Timetable** – weekly repeating slots (e.g. Amy Mon–Fri 20:00–22:00) plus one-off shifts. Warns about overlaps. Overnight shifts (22:00–02:00) work.
- **Streamers** – add/edit streamers, test the live check, deactivate someone who left.
- **Report** – per streamer for any date range: attendance % (live time ÷ scheduled time), punctuality %, late, missed, went offline, ended early. Download as CSV (for payroll / KPI). Worst performers listed first.
- **Shift details** – minute-by-minute check log for disputes ("I was live!").
- **Streamer personal link** (`/c/<code>`, no login) – each streamer sees their own upcoming shifts on their phone. Send it to them once.

## Supported platforms

| Platform | How it's checked | Notes |
|---|---|---|
| `tiktok` | public live page of `@handle` | TikTok has no official API; works without setup but may break if TikTok changes its page — the "Can't verify" alert tells you. |
| `youtube` | `@handle` or `UC…` channel ID live page; Data API if `TP_YOUTUBE_API_KEY` set with a `UC…` id | |
| `twitch` | official Helix API | needs `TP_TWITCH_CLIENT_ID` / `SECRET` (free at dev.twitch.tv) |
| `manual` | streamer taps **"I'm LIVE now"** on their personal link | for Shopee / Lazada / Facebook / anything else. Trust-based — spot-check these. |

Use the **Test live check** button on the Streamers page to confirm each channel is detected correctly.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in password + Telegram (see below)
set -a; . ./.env; set +a
python app.py             # web UI + monitor on http://localhost:5000
```

Try it with sample data first: `TP_DATABASE=demo.db python seed_demo.py && TP_DATABASE=demo.db python app.py`

**Telegram alerts (recommended):** message `@BotFather` → `/newbot` → copy the token into `TP_TELEGRAM_BOT_TOKEN`.
Add the bot to your group (or message it), then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the `chat.id` into `TP_TELEGRAM_CHAT_ID`.

**Run 24/7:** the monitor must be running during shifts, so host it on an always-on machine or a small VPS / Render / Railway instance (keep the `.db` file on persistent disk). Run one process only — the monitor runs inside `app.py`.
Shifts that pass while the app is off are marked *Not checked* and left out of reports.

## Tests

```bash
python -m pytest
```
