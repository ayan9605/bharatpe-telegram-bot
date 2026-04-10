"""
Payment session manager — backed by PostgreSQL.
"""

import time
from datetime import datetime, timedelta
from config import TIMEOUT_SECONDS
from database import insert_payment, mark_success, mark_failure, is_amount_in_use, get_payment


class Session:
    """Lightweight session object passed around during a payment flow."""
    __slots__ = (
        "order_id", "base_amount", "amount",
        "created_at", "expire_at", "status", "utr", "vpa", "chat_id",
    )

    def __init__(self, order_id, base_amount, amount, chat_id):
        self.order_id = order_id
        self.base_amount = base_amount
        self.amount = amount
        self.chat_id = chat_id
        self.created_at = datetime.now()
        self.expire_at = self.created_at + timedelta(seconds=TIMEOUT_SECONDS)
        self.status = "PENDING"
        self.utr = ""
        self.vpa = ""

    @property
    def is_active(self) -> bool:
        return self.status == "PENDING" and self.expire_at > datetime.now()


def create_session(base_amount: float, chat_id: int, username: str = "") -> Session:
    """Create a payment session with a unique micro-amount, persisted in PostgreSQL."""
    order_id = f"TG{int(time.time())}{int(base_amount * 100):05d}"

    for i in range(100):
        candidate = round(base_amount + 0.01 * i, 2)
        if not is_amount_in_use(candidate):
            session = Session(order_id, base_amount, candidate, chat_id)
            insert_payment(
                order_id=order_id,
                chat_id=chat_id,
                username=username,
                base_amount=base_amount,
                session_amount=candidate,
                expire_at=session.expire_at,
            )
            return session

    raise RuntimeError("Too many concurrent payments. Please wait a moment.")


def complete_session(order_id: str, utr: str, vpa: str = ""):
    """Mark a session as successfully paid."""
    mark_success(order_id, utr, vpa)


def expire_session(order_id: str):
    """Mark a session as failed/expired."""
    mark_failure(order_id)


def load_session(order_id: str) -> dict | None:
    """Load a session from DB."""
    return get_payment(order_id)
