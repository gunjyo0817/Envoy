"""Google OAuth + Calendar v3 REST via raw httpx. No google client lib."""
import os, datetime, urllib.parse
import httpx
from app import store

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8000/calendar/callback")
SCOPE = "openid email profile https://www.googleapis.com/auth/calendar"
TZ = os.environ.get("ENVOY_TZ", "Europe/Berlin")

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CAL = "https://www.googleapis.com/calendar/v3"


def auth_url(state: str) -> str:
    params = {
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def _expiry_from_now(seconds: int) -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=seconds)).isoformat()


def exchange_code(code: str) -> dict:
    """Exchange an auth code -> {access_token, refresh_token, expiry}."""
    resp = httpx.post(_TOKEN_URL, data={
        "code": code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code",
    }, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expiry": _expiry_from_now(int(data.get("expires_in", 3600))),
    }


def valid_access_token(user_id: int) -> str | None:
    """Return a non-expired access token, refreshing via the refresh token if needed."""
    tok = store.get_google_tokens(user_id)
    if not tok:
        return None
    try:
        expiry = datetime.datetime.fromisoformat(tok["expiry"])
    except (ValueError, TypeError):
        expiry = datetime.datetime.now(datetime.timezone.utc)
    if expiry > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60):
        return tok["access_token"]
    if not tok.get("refresh_token"):
        return tok["access_token"]
    resp = httpx.post(_TOKEN_URL, data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
    }, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    new_access = data["access_token"]
    store.update_google_access(user_id, new_access, _expiry_from_now(int(data.get("expires_in", 3600))))
    return new_access


def query_freebusy(user_id: int, time_min_iso: str, time_max_iso: str) -> list[dict]:
    """Return the user's busy intervals [{start, end}] in the window, or [] if unavailable."""
    token = valid_access_token(user_id)
    if not token:
        return []
    try:
        resp = httpx.post(f"{_CAL}/freeBusy", headers={"Authorization": f"Bearer {token}"},
                          json={"timeMin": time_min_iso, "timeMax": time_max_iso,
                                "items": [{"id": "primary"}]}, timeout=10.0)
        resp.raise_for_status()
        return resp.json()["calendars"]["primary"].get("busy", [])
    except Exception:
        return []


def insert_event(user_id: int, summary: str, location: str,
                 start_iso: str, end_iso: str) -> dict | None:
    """Insert a calendar event; return {htmlLink} or None if not connected/failed."""
    token = valid_access_token(user_id)
    if not token:
        return None
    resp = httpx.post(
        f"{_CAL}/calendars/primary/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "summary": summary, "location": location,
            "start": {"dateTime": start_iso, "timeZone": TZ},
            "end": {"dateTime": end_iso, "timeZone": TZ},
        }, timeout=10.0)
    resp.raise_for_status()
    return {"htmlLink": resp.json().get("htmlLink")}
