"""
Payment handler — full pay flow with QR, polling, and result.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

from config import TIMEOUT, POLL_INTERVAL, MIN_AMOUNT, MAX_AMOUNT
from bharatpe import find_payment
from qr_generator import make_qr
from database import (
    is_amount_in_use, insert_payment, complete_payment,
    fail_payment, expire_stale, log_activity,
)
from .keyboards import amounts_kb, waiting_kb, result_kb, home_kb
from .middleware import track_user, check_blocked, check_rate_limit

log = logging.getLogger(__name__)


# ✅ helper for safe rounding
def normalize(val: float) -> float:
    return float(Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class ActiveSession:
    __slots__ = ("order_id", "amount", "created_at", "expire_at", "status", "chat_id")

    def __init__(self, order_id, amount, chat_id):
        self.order_id = order_id
        self.amount = amount
        self.chat_id = chat_id
        self.created_at = datetime.now()
        self.expire_at = self.created_at + timedelta(seconds=TIMEOUT)
        self.status = "PENDING"


def _make_order_id(amount: float) -> str:
    return f"TG{int(time.time())}{int(amount * 100):05d}"


# ✅ UPDATED DECIMAL LOGIC (₹x.01 → ₹x.10 ONLY)
def _find_free_amount(base: float) -> float | None:
    base = normalize(base)

    for i in range(1, 11):  # 1 → 10
        candidate = normalize(base + (i / 100))

        if not is_amount_in_use(candidate):
            return candidate

    return None


# ── /pay command ───────────────────────────────────────

async def cmd_pay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await track_user(update)
    if await check_blocked(update):
        return

    if ctx.args:
        try:
            await _start_payment(update.message, ctx, float(ctx.args[0]))
            return
        except ValueError:
            pass

    await update.message.reply_text("Select amount or enter custom:", reply_markup=amounts_kb())


# ── Button: pay:* ─────────────────────────────────────

async def on_pay_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, action = q.data.split(":", 1)

    if action == "start" or action == "custom":
        if await check_blocked(update):
            return
        await q.message.reply_text("Enter the amount (₹):")
        ctx.user_data["input"] = "pay_amount"

    elif action == "cancel":
        oid = ctx.user_data.pop("active_order", None)
        if oid:
            fail_payment(oid)
            log_activity(q.from_user.id, "cancel", oid)
        await q.message.reply_text("❌ Payment cancelled.", reply_markup=result_kb(q.from_user.id))

    else:
        if await check_blocked(update):
            return
        await _start_payment(q.message, ctx, float(action))


# ── Text input for amount ──────────────────────────────

async def on_amount_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if ctx.user_data.get("input") != "pay_amount":
        return

    ctx.user_data.pop("input", None)
    text = update.message.text.strip().replace("₹", "").replace(",", "")

    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number. Example: 100")
        return

    await _start_payment(update.message, ctx, amount)


# ── Core payment flow ─────────────────────────────────

async def _start_payment(message, ctx: ContextTypes.DEFAULT_TYPE, amount: float):
    uid = message.chat_id
    amount = normalize(amount)

    # Validate
    if amount < MIN_AMOUNT:
        await message.reply_text(f"❌ Minimum ₹{MIN_AMOUNT}")
        return
    if amount > MAX_AMOUNT:
        await message.reply_text(f"❌ Maximum ₹{MAX_AMOUNT:,}")
        return

    # Rate limit
    err = await check_rate_limit(Update(0, message=message))
    if err:
        await message.reply_text(err)
        return

    expire_stale()

    # ✅ use updated decimal logic
    session_amount = _find_free_amount(amount)
    if session_amount is None:
        await message.reply_text("⚠️ Too many concurrent payments. Try again shortly.", reply_markup=result_kb(uid))
        return

    session_amount = normalize(session_amount)

    order_id = _make_order_id(amount)
    expire_at = datetime.now() + timedelta(seconds=TIMEOUT)

    s = ActiveSession(order_id, session_amount, uid)
    ctx.user_data["active_order"] = order_id

    log.info(f"NEW | {order_id} | ₹{session_amount} | chat={uid}")
    log_activity(uid, "payment_start", f"{order_id} ₹{session_amount}")

    # QR
    qr_buf = make_qr(session_amount, order_id)

    qr_msg = await message.reply_photo(
        photo=qr_buf,
        caption=(
            f"💳 Pay ₹{session_amount:.2f}\n\n"
            f"📱 Scan with any UPI app\n"
            f"⚠️ Pay exactly ₹{session_amount:.2f}\n"
            f"⏱ {TIMEOUT // 60} min timeout\n\n"
            f"🔄 Verifying..."
        ),
        reply_markup=waiting_kb(),
    )

    insert_payment(order_id, uid, amount, session_amount, expire_at, qr_msg.message_id)

    # ── Poll loop ──────────────────────────────────────
    elapsed = 0

    while elapsed < TIMEOUT:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        if s.status != "PENDING":
            break

        match = find_payment(normalize(s.amount), s.created_at, s.expire_at)

        if match:
            s.status = "SUCCESS"
            complete_payment(order_id, match["utr"], match.get("vpa", ""))
            log_activity(uid, "payment_success", f"{order_id} UTR={match['utr']}")

            try:
                await qr_msg.edit_caption(
                    caption=f"💳 ₹{s.amount:.2f}\n\n✅ Payment Verified"
                )
            except Exception:
                pass

            await qr_msg.reply_text(
                f"✅ Payment Successful!\n\n"
                f"💰 Amount: ₹{match['amount']:.2f}\n"
                f"🔗 UTR: {match['utr']}\n"
                f"👤 From: {match.get('vpa') or 'N/A'}\n"
                f"🕐 {match['timestamp']}\n"
                f"📝 {order_id}",
                reply_markup=result_kb(uid),
            )

            ctx.user_data.pop("active_order", None)
            return

    # ── Expired ────────────────────────────────────────
    if s.status == "PENDING":
        fail_payment(order_id)
        log_activity(uid, "payment_expired", order_id)

    try:
        await qr_msg.edit_caption(
            caption=f"💳 ₹{s.amount:.2f}\n\n❌ Expired"
        )
    except Exception:
        pass

    await qr_msg.reply_text(
        f"❌ Payment Expired\n\n"
        f"No payment received in {TIMEOUT // 60} min.\n"
        f"Order: {order_id}",
        reply_markup=result_kb(uid),
    )

    ctx.user_data.pop("active_order", None)


def register_payment_handlers(app):
    app.add_handler(CommandHandler("pay", cmd_pay))
    app.add_handler(CallbackQueryHandler(on_pay_button, pattern=r"^pay:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_amount_text), group=1)
