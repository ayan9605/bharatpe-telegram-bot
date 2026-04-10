"""PostgreSQL database layer."""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
from config import DB_URL

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    chat_id         BIGINT UNIQUE NOT NULL,
    username        VARCHAR(128),
    first_name      VARCHAR(128),
    is_blocked      BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    total_paid      NUMERIC(14,2) NOT NULL DEFAULT 0,
    payment_count   INT NOT NULL DEFAULT 0,
    failed_count    INT NOT NULL DEFAULT 0,
    first_seen      TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id              SERIAL PRIMARY KEY,
    order_id        VARCHAR(64) UNIQUE NOT NULL,
    chat_id         BIGINT NOT NULL REFERENCES users(chat_id),
    base_amount     NUMERIC(12,2) NOT NULL,
    session_amount  NUMERIC(12,2) NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    utr             VARCHAR(64),
    payer_vpa       VARCHAR(128),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    expire_at       TIMESTAMP NOT NULL,
    completed_at    TIMESTAMP,
    message_id      BIGINT
);

CREATE INDEX IF NOT EXISTS idx_pay_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_pay_chat ON payments(chat_id);
CREATE INDEX IF NOT EXISTS idx_pay_amount ON payments(session_amount) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_pay_created ON payments(created_at);

CREATE TABLE IF NOT EXISTS activity_log (
    id              SERIAL PRIMARY KEY,
    chat_id         BIGINT,
    action          VARCHAR(64) NOT NULL,
    detail          TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


@contextmanager
def get_db():
    """Context-managed database connection."""
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
    log.info("Database initialized")


def log_activity(chat_id: int, action: str, detail: str = ""):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO activity_log (chat_id, action, detail) VALUES (%s, %s, %s)",
                        (chat_id, action, detail))


# ── Users ──────────────────────────────────────────────

def upsert_user(chat_id: int, username: str = None, first_name: str = None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (chat_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE
                SET username = COALESCE(EXCLUDED.username, users.username),
                    first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                    last_seen = NOW()
            """, (chat_id, username, first_name))


def is_blocked(chat_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT is_blocked FROM users WHERE chat_id = %s", (chat_id,))
            row = cur.fetchone()
            return row[0] if row else False


def get_user(chat_id: int) -> dict | None:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
            return cur.fetchone()


def block_user(chat_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_blocked = TRUE WHERE chat_id = %s", (chat_id,))
            return cur.rowcount > 0


def unblock_user(chat_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_blocked = FALSE WHERE chat_id = %s", (chat_id,))
            return cur.rowcount > 0


# ── Payments ───────────────────────────────────────────

def is_amount_in_use(amount: float) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM payments
                WHERE ABS(session_amount - %s) < 0.001 AND status = 'PENDING' AND expire_at > NOW()
                LIMIT 1
            """, (amount,))
            return cur.fetchone() is not None


def insert_payment(order_id: str, chat_id: int, base_amount: float,
                   session_amount: float, expire_at: datetime, message_id: int = None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments (order_id, chat_id, base_amount, session_amount, expire_at, message_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (order_id, chat_id, base_amount, session_amount, expire_at, message_id))


def complete_payment(order_id: str, utr: str, vpa: str = ""):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE payments SET status='SUCCESS', utr=%s, payer_vpa=%s, completed_at=NOW()
                WHERE order_id=%s AND status='PENDING'
                RETURNING chat_id, session_amount
            """, (utr, vpa, order_id))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    UPDATE users SET total_paid = total_paid + %s, payment_count = payment_count + 1
                    WHERE chat_id = %s
                """, (row["session_amount"], row["chat_id"]))


def fail_payment(order_id: str):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE payments SET status='FAILURE'
                WHERE order_id=%s AND status='PENDING'
                RETURNING chat_id
            """, (order_id,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE users SET failed_count = failed_count + 1 WHERE chat_id = %s",
                            (row["chat_id"],))


def get_payment(order_id: str) -> dict | None:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM payments WHERE order_id = %s", (order_id,))
            return cur.fetchone()


def expire_stale():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE payments SET status='FAILURE' WHERE status='PENDING' AND expire_at < NOW()")
            return cur.rowcount


def user_history(chat_id: int, limit: int = 10) -> list[dict]:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT order_id, session_amount, status, utr, payer_vpa, created_at, completed_at
                FROM payments WHERE chat_id = %s ORDER BY created_at DESC LIMIT %s
            """, (chat_id, limit))
            return cur.fetchall()


def user_active_count(chat_id: int) -> int:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM payments WHERE chat_id=%s AND status='PENDING' AND expire_at > NOW()",
                        (chat_id,))
            return cur.fetchone()[0]


def user_hourly_count(chat_id: int) -> int:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM payments WHERE chat_id=%s AND created_at > NOW() - INTERVAL '1 hour'",
                        (chat_id,))
            return cur.fetchone()[0]


# ── Admin ──────────────────────────────────────────────

def admin_dashboard() -> dict:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status='SUCCESS') AS success,
                    COUNT(*) FILTER (WHERE status='FAILURE') AS failed,
                    COUNT(*) FILTER (WHERE status='PENDING') AS pending,
                    COALESCE(SUM(session_amount) FILTER (WHERE status='SUCCESS'), 0) AS revenue,
                    COALESCE(SUM(session_amount) FILTER (WHERE status='SUCCESS' AND created_at::date = CURRENT_DATE), 0) AS today_rev,
                    COUNT(*) FILTER (WHERE status='SUCCESS' AND created_at::date = CURRENT_DATE) AS today_count
                FROM payments
            """)
            d = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS c FROM users")
            d["users"] = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM users WHERE last_seen > NOW() - INTERVAL '24 hours'")
            d["active"] = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM users WHERE is_blocked")
            d["blocked"] = cur.fetchone()["c"]
            return d


def admin_recent(limit: int = 10) -> list[dict]:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.*, u.username, u.first_name
                FROM payments p LEFT JOIN users u ON p.chat_id = u.chat_id
                ORDER BY p.created_at DESC LIMIT %s
            """, (limit,))
            return cur.fetchall()


def admin_users(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM users ORDER BY total_paid DESC LIMIT %s
            """, (limit,))
            return cur.fetchall()


def admin_search(q: str) -> dict | None:
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM payments WHERE order_id=%s OR utr=%s LIMIT 1", (q, q))
            return cur.fetchone()
