"""
Pay0 Telegram Payment Bot — Entry Point

Structure:
  bot.py              ← you are here
  config.py           ← env-based configuration
  database.py         ← PostgreSQL layer
  bharatpe.py         ← BharatPe transaction API
  qr_generator.py     ← branded UPI QR codes
  session.py          ← session helpers
  handlers/
    __init__.py       ← handler registration
    keyboards.py      ← shared keyboard layouts
    middleware.py      ← auth, rate limit, user tracking
    member.py         ← /start, history, stats, help
    payment.py        ← /pay, QR flow, polling
    admin.py          ← /admin, dashboard, members, broadcast
"""

import logging
from telegram.ext import Application
from config import BOT_TOKEN, MERCHANT_NAME
from database import init_db
from handlers import register_member_handlers, register_admin_handlers, register_payment_handlers

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("pay0bot")


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    register_member_handlers(app)
    register_payment_handlers(app)
    register_admin_handlers(app)

    log.info(f"{MERCHANT_NAME} Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
