"""Member handlers — start, history, stats, help, navigation."""

import logging
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from .keyboards import home_kb, is_admin
from .middleware import track_user
from database import user_history, get_user, log_activity
from config import MERCHANT_NAME

log = logging.getLogger(__name__)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await track_user(update)
    uid = update.effective_user.id
    name = update.effective_user.first_name or "there"

    admin_line = "\n🔐 Admin access enabled." if is_admin(uid) else ""

    await update.message.reply_text(
        f"Hey {name}! 👋\n\n"
        f"*{MERCHANT_NAME}* — Instant UPI Payments\n\n"
        f"💳 Pay via QR — right here in chat\n"
        f"📱 Works with all UPI apps\n"
        f"🔒 Verified automatically via BharatPe\n"
        f"💸 0% transaction fee{admin_line}\n\n"
        f"Tap a button below to begin:",
        reply_markup=home_kb(uid),
        parse_mode="Markdown",
    )
    log_activity(uid, "start")


async def on_nav(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle nav: buttons."""
    q = update.callback_query
    await q.answer()
    _, action = q.data.split(":", 1)

    if action == "home":
        await track_user(update)
        await q.message.reply_text("Choose an option:", reply_markup=home_kb(q.from_user.id))


async def on_me(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle me: buttons (history, stats, help)."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    _, action = q.data.split(":", 1)

    if action == "history":
        rows = user_history(uid, limit=10)
        if not rows:
            await q.message.reply_text("No payments yet.\n\nTap *Pay Now* to start!",
                                       reply_markup=home_kb(uid), parse_mode="Markdown")
            return

        lines = ["📋 *Payment History*\n"]
        for r in rows:
            icon = {"SUCCESS": "✅", "FAILURE": "❌", "PENDING": "⏳"}.get(r["status"], "❓")
            t = r["created_at"].strftime("%d/%m %H:%M")
            utr = f"\n     UTR: `{r['utr']}`" if r.get("utr") else ""
            lines.append(f"{icon} *₹{r['session_amount']:.2f}* — {t}{utr}")

        await q.message.reply_text("\n".join(lines), reply_markup=home_kb(uid), parse_mode="Markdown")

    elif action == "stats":
        u = get_user(uid)
        if not u:
            await q.message.reply_text("No data yet.", reply_markup=home_kb(uid))
            return

        rate = (u["payment_count"] / max(u["payment_count"] + u["failed_count"], 1)) * 100

        await q.message.reply_text(
            f"📊 *Your Stats*\n\n"
            f"💰 Total Paid: *₹{u['total_paid']:,.2f}*\n"
            f"✅ Successful: *{u['payment_count']}*\n"
            f"❌ Failed: *{u['failed_count']}*\n"
            f"📈 Success Rate: *{rate:.0f}%*\n"
            f"📅 Member Since: {u['first_seen'].strftime('%d %b %Y')}",
            reply_markup=home_kb(uid),
            parse_mode="Markdown",
        )

    elif action == "help":
        await q.message.reply_text(
            f"*{MERCHANT_NAME} — How It Works*\n\n"
            f"1️⃣ Tap *Pay Now* or select a quick amount\n"
            f"2️⃣ A UPI QR code appears in chat\n"
            f"3️⃣ Open any UPI app (GPay, PhonePe, Paytm, BHIM)\n"
            f"4️⃣ Scan the QR and pay the *exact* amount\n"
            f"5️⃣ Payment is verified automatically ✅\n\n"
            f"*Important:*\n"
            f"• Pay the exact amount including paise\n"
            f"• You have 5 minutes to complete\n"
            f"• Don't close the chat while paying\n\n"
            f"*Commands:*\n"
            f"/pay <amount> — Quick pay\n"
            f"/start — Main menu",
            reply_markup=home_kb(uid),
            parse_mode="Markdown",
        )


def register_member_handlers(app):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_nav, pattern=r"^nav:"))
    app.add_handler(CallbackQueryHandler(on_me, pattern=r"^me:"))
