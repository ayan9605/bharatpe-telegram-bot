"""Pre-check middleware — block checks, rate limits, user tracking."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import upsert_user, is_blocked, user_active_count, user_hourly_count
from config import MAX_PAYMENTS_PER_HOUR, MAX_CONCURRENT_PAYMENTS

log = logging.getLogger(__name__)


async def track_user(update: Update):
    """Track user in DB on every interaction."""
    u = update.effective_user
    if u:
        upsert_user(u.id, u.username, u.first_name)


async def check_blocked(update: Update) -> bool:
    """Return True if user is blocked."""
    u = update.effective_user
    if u and is_blocked(u.id):
        msg = update.message or update.callback_query.message
        await msg.reply_text("🚫 Your account is blocked. Contact admin.")
        return True
    return False


async def check_rate_limit(update: Update) -> str | None:
    """Return error message if rate limited, None if OK."""
    uid = update.effective_user.id

    active = user_active_count(uid)
    if active >= MAX_CONCURRENT_PAYMENTS:
        return f"⚠️ You have {active} active payment(s). Complete or wait for them to expire."

    hourly = user_hourly_count(uid)
    if hourly >= MAX_PAYMENTS_PER_HOUR:
        return f"⚠️ Rate limit: max {MAX_PAYMENTS_PER_HOUR} payments per hour."

    return None
