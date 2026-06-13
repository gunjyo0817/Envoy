"""Persistence for completed deals and Telegram chat links (stdlib sqlite3)."""
import os, json, sqlite3, datetime

_DB_PATH = os.environ.get("ENVOY_DB", os.path.join(os.path.dirname(__file__), "..", "envoy.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(os.environ.get("ENVOY_DB", _DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_store() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS telegram_links (
                chat_id    INTEGER PRIMARY KEY,
                role       TEXT NOT NULL,
                user_id    INTEGER,
                session_id TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS deals (
                session_id   TEXT PRIMARY KEY,
                user_id      INTEGER,
                query        TEXT,
                thumbnail    TEXT,
                final_price  REAL,
                seller_label TEXT,
                meetup       TEXT,
                status       TEXT,
                created_at   TEXT,
                closed_at    TEXT,
                negotiation_thread TEXT
            )"""
        )
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(deals)").fetchall()]
        if "negotiation_thread" not in cols:
            conn.execute("ALTER TABLE deals ADD COLUMN negotiation_thread TEXT")


def register_chat(chat_id: int, role: str, user_id: int | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO telegram_links (chat_id, role, user_id) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET role=excluded.role, user_id=excluded.user_id",
            (chat_id, role, user_id),
        )


def attach_session(chat_id: int, session_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE telegram_links SET session_id=? WHERE chat_id=?", (session_id, chat_id))


def resolve_chat(chat_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM telegram_links WHERE chat_id=?", (chat_id,)).fetchone()
    return dict(row) if row else None


def chat_for_role(role: str) -> int | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT chat_id FROM telegram_links WHERE role=? ORDER BY rowid DESC LIMIT 1", (role,)
        ).fetchone()
    return row["chat_id"] if row else None


def record_deal(deal: dict) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO deals
               (session_id, user_id, query, thumbnail, final_price, seller_label, meetup, status,
                created_at, closed_at, negotiation_thread)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 final_price=excluded.final_price, meetup=excluded.meetup,
                 status=excluded.status, closed_at=excluded.closed_at,
                 negotiation_thread=excluded.negotiation_thread""",
            (deal["session_id"], deal.get("user_id"), deal.get("query"), deal.get("thumbnail"),
             deal.get("final_price"), deal.get("seller_label"),
             json.dumps(deal.get("meetup") or {}), deal.get("status"), now, now,
             json.dumps(deal.get("negotiation_thread") or [])),
        )


def _row_to_deal(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["meetup"] = json.loads(d.get("meetup") or "{}")
    d["negotiation_thread"] = json.loads(d.get("negotiation_thread") or "[]")
    return d


def list_deals(user_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM deals WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
    return [_row_to_deal(r) for r in rows]


def get_deal(session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM deals WHERE session_id=?", (session_id,)).fetchone()
    return _row_to_deal(row) if row else None
