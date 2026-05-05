"""
Pay0 Telegram Payment Bot — Entry Point (with FastAPI wrapper)
"""

import logging
import threading
from fastapi import FastAPI
from telegram.ext import Application
from config import BOT_TOKEN, MERCHANT_NAME
from database import init_db
from handlers import register_member_handlers, register_admin_handlers, register_payment_handlers

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("pay0bot")

# ---- EXISTING LOGIC (UNCHANGED) ----
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    register_member_handlers(app)
    register_payment_handlers(app)
    register_admin_handlers(app)

    log.info(f"{MERCHANT_NAME} Bot started")
    app.run_polling()


# ---- FASTAPI WRAPPER ----
api = FastAPI()


@api.get("/")
def root():
    return {"status": "Pay0 bot is running"}


@api.get("/health")
def health():
    return {"ok": True}


def start_bot():
    """Run bot in a separate thread"""
    main()


@api.on_event("startup")
def startup_event():
    thread = threading.Thread(target=start_bot)
    thread.daemon = True
    thread.start()
