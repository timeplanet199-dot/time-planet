"""Stores alerts and pushes them to Telegram / Discord / a webhook."""
import logging

import requests

import config
import db

log = logging.getLogger("timeplanet.alerts")
ICONS = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}


def raise_alert(conn, shift_id, kind, severity, message, once=True):
    """Record an alert; with once=True a shift only gets each kind one time."""
    if once and conn.execute(
        "SELECT 1 FROM alerts WHERE shift_id = ? AND kind = ?", (shift_id, kind)
    ).fetchone():
        return False
    conn.execute(
        "INSERT INTO alerts (shift_id, kind, severity, message, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (shift_id, kind, severity, message, db.iso(db.now())),
    )
    send(f"{ICONS.get(severity, '')} {message}")
    return True


def send(text):
    log.warning("ALERT %s", text)
    targets = []
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        targets.append((
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            {"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
        ))
    if config.DISCORD_WEBHOOK_URL:
        targets.append((config.DISCORD_WEBHOOK_URL, {"content": text}))
    if config.GENERIC_WEBHOOK_URL:
        targets.append((config.GENERIC_WEBHOOK_URL, {"text": text}))
    for url, payload in targets:
        try:
            requests.post(url, json=payload, timeout=10).raise_for_status()
        except Exception as exc:
            log.error("alert delivery failed: %s", exc)
