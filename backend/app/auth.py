"""Minimal real auth + per-user settings, stdlib only (sqlite3 + pbkdf2)."""
import os, sqlite3, hashlib, secrets, hmac

_DB_PATH = os.environ.get("BUYBOT_DB", os.path.join(os.path.dirname(__file__), "..", "buybot.db"))
# token -> user_id (in-memory; resets on restart, fine for the hackathon)
_TOKENS: dict[str, int] = {}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                pw_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'en',
                default_address TEXT NOT NULL DEFAULT ''
            )"""
        )


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


def _issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = user_id
    return token


class AuthError(Exception):
    """Raised on signup/login failures; carries an HTTP-ish code."""
    def __init__(self, code: int, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def signup(email: str, password: str, name: str = "") -> dict:
    email = email.strip().lower()
    if not email or not password:
        raise AuthError(400, "Email and password required")
    salt = secrets.token_hex(16)
    pw_hash = _hash(password, salt)
    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (email, name, pw_hash, salt) VALUES (?, ?, ?, ?)",
                (email, name, pw_hash, salt),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise AuthError(409, "Email already registered")
    return {"token": _issue_token(user_id), "user": _public_user(user_id)}


def login(email: str, password: str) -> dict:
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not hmac.compare_digest(row["pw_hash"], _hash(password, row["salt"])):
        raise AuthError(401, "Invalid email or password")
    return {"token": _issue_token(row["id"]), "user": _public_user(row["id"])}


def user_id_for_token(token: str | None) -> int | None:
    if not token:
        return None
    return _TOKENS.get(token)


def _public_user(user_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, name, language, default_address FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else {}


def get_settings(user_id: int) -> dict:
    u = _public_user(user_id)
    return {"language": u.get("language", "en"), "default_address": u.get("default_address", "")}


def update_settings(user_id: int, language: str | None, default_address: str | None) -> dict:
    with _connect() as conn:
        if language is not None:
            conn.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
        if default_address is not None:
            conn.execute("UPDATE users SET default_address = ? WHERE id = ?", (default_address, user_id))
    return get_settings(user_id)
