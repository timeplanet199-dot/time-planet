"""Live-status checkers, one per platform.

Each checker returns a LiveStatus. `is_live=None` means "could not tell"
(network error, blocked page); the monitor does not count that as offline.
"""
import json
import re
import time
from dataclasses import dataclass

import requests

import config
import db

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 15


@dataclass
class LiveStatus:
    is_live: bool | None
    viewers: int | None = None
    detail: str = ""


def check(streamer):
    checker = CHECKERS.get(streamer["platform"])
    if checker is None:
        return LiveStatus(None, detail=f"unknown platform {streamer['platform']}")
    try:
        return checker(streamer)
    except Exception as exc:  # never let one channel stop the monitor
        return LiveStatus(None, detail=f"error: {exc}"[:300])


def check_manual(streamer):
    """Streamer taps 'I'm live' on their check-in page, which sets a heartbeat."""
    until = db.parse(streamer["manual_live_until"])
    live = bool(until and until >= db.now())
    return LiveStatus(live, detail="check-in heartbeat" if live else "no check-in")


def check_tiktok(streamer):
    """Unofficial: reads the public live page. TikTok has no public live API."""
    handle = streamer["handle"].lstrip("@")
    resp = requests.get(
        f"https://www.tiktok.com/@{handle}/live", headers=HEADERS, timeout=TIMEOUT
    )
    if resp.status_code != 200:
        return LiveStatus(None, detail=f"tiktok http {resp.status_code}")
    html = resp.text
    # LiveRoom status: 2 = live, 4 = ended
    match = re.search(r'"liveRoom"\s*:\s*\{.*?"status"\s*:\s*(\d+)', html, re.S)
    if not match:
        match = re.search(r'"roomInfo".*?"status"\s*:\s*(\d+)', html, re.S)
    if not match:
        return LiveStatus(None, detail="tiktok page format not recognised")
    viewers = re.search(r'"userCount"\s*:\s*(\d+)', html)
    return LiveStatus(
        match.group(1) == "2",
        int(viewers.group(1)) if viewers else None,
        f"tiktok room status {match.group(1)}",
    )


def check_youtube(streamer):
    handle = streamer["handle"]
    if config.YOUTUBE_API_KEY and handle.startswith("UC"):
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "id", "channelId": handle, "eventType": "live",
                "type": "video", "key": config.YOUTUBE_API_KEY,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return LiveStatus(bool(resp.json().get("items")), detail="youtube api")
    path = f"channel/{handle}" if handle.startswith("UC") else f"@{handle.lstrip('@')}"
    resp = requests.get(
        f"https://www.youtube.com/{path}/live", headers=HEADERS, timeout=TIMEOUT,
        cookies={"CONSENT": "YES+1"},
    )
    if resp.status_code != 200:
        return LiveStatus(None, detail=f"youtube http {resp.status_code}")
    live = '"isLiveNow":true' in resp.text
    viewers = re.search(r'"originalViewCount":"(\d+)"', resp.text)
    return LiveStatus(
        live, int(viewers.group(1)) if live and viewers else None, "youtube page"
    )


_twitch_token = {"value": None, "expires": 0}


def _twitch_app_token():
    if _twitch_token["value"] and _twitch_token["expires"] > time.time() + 60:
        return _twitch_token["value"]
    resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": config.TWITCH_CLIENT_ID,
            "client_secret": config.TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    _twitch_token.update(value=data["access_token"], expires=time.time() + data["expires_in"])
    return data["access_token"]


def check_twitch(streamer):
    if not (config.TWITCH_CLIENT_ID and config.TWITCH_CLIENT_SECRET):
        return LiveStatus(None, detail="twitch credentials not configured")
    resp = requests.get(
        "https://api.twitch.tv/helix/streams",
        params={"user_login": streamer["handle"].lstrip("@")},
        headers={
            "Client-Id": config.TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {_twitch_app_token()}",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    streams = resp.json().get("data", [])
    if not streams:
        return LiveStatus(False, detail="twitch api")
    return LiveStatus(True, streams[0].get("viewer_count"), json.dumps(streams[0].get("title", ""))[:200])


CHECKERS = {
    "manual": check_manual,
    "tiktok": check_tiktok,
    "youtube": check_youtube,
    "twitch": check_twitch,
}
PLATFORMS = list(CHECKERS)
