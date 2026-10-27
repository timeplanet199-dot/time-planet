"""All settings come from environment variables (see .env.example)."""
import os
from zoneinfo import ZoneInfo


def _int(name, default):
    return int(os.environ.get(name, default))


TIMEZONE = ZoneInfo(os.environ.get("TP_TIMEZONE", "Asia/Kuala_Lumpur"))
DATABASE = os.environ.get("TP_DATABASE", "timeplanet.db")
ADMIN_PASSWORD = os.environ.get("TP_ADMIN_PASSWORD", "")  # empty = no login
SECRET_KEY = os.environ.get("TP_SECRET_KEY", "change-me")
PUBLIC_URL = os.environ.get("TP_PUBLIC_URL", "http://localhost:5000")

# Monitoring rules (minutes)
CHECK_INTERVAL_SECONDS = _int("TP_CHECK_INTERVAL_SECONDS", 120)
GRACE_MINUTES = _int("TP_GRACE_MINUTES", 5)          # allowed lateness before "late"
NO_SHOW_MINUTES = _int("TP_NO_SHOW_MINUTES", 20)     # not live by then = "no show"
DROP_CHECKS = _int("TP_DROP_CHECKS", 2)              # consecutive offline checks = "dropped"
EARLY_END_MINUTES = _int("TP_EARLY_END_MINUTES", 10)  # stopped this early = "ended early"
MANUAL_HEARTBEAT_MINUTES = _int("TP_MANUAL_HEARTBEAT_MINUTES", 15)
SCHEDULE_DAYS_AHEAD = _int("TP_SCHEDULE_DAYS_AHEAD", 14)

# Alerts
TELEGRAM_BOT_TOKEN = os.environ.get("TP_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TP_TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.environ.get("TP_DISCORD_WEBHOOK_URL", "")
GENERIC_WEBHOOK_URL = os.environ.get("TP_WEBHOOK_URL", "")

# Platform credentials (optional; improves reliability)
TWITCH_CLIENT_ID = os.environ.get("TP_TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.environ.get("TP_TWITCH_CLIENT_SECRET", "")
YOUTUBE_API_KEY = os.environ.get("TP_YOUTUBE_API_KEY", "")
