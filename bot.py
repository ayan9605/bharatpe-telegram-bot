"""
Pay0 Telegram Payment Bot — Entry Point (Auto Webhook + FastAPI)
"""

import logging
import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from config import BOT_TOKEN, MERCHANT_NAME
from database import init_db
from handlers import (
    register_member_handlers,
    register_admin_handlers,
    register_payment_handlers,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("pay0bot")

# ---- INIT ----
init_db()

application = Application.builder().token(BOT_TOKEN).build()

register_member_handlers(application)
register_payment_handlers(application)
register_admin_handlers(application)

# ---- FASTAPI ----
api = FastAPI()

WEBHOOK_PATH = "/webhook"


def get_webhook_url():
    """
    Auto-detect webhook URL from environment
    Supports Render, Railway, custom deployments
    """
    base_url = (
        os.getenv("RENDER_EXTERNAL_URL") or
        os.getenv("RAILWAY_PUBLIC_DOMAIN") or
        os.getenv("WEBHOOK_BASE_URL")
    )

    if not base_url:
        raise ValueError("No public URL found for webhook")

    # Railway gives only domain → fix it
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"

    return f"{base_url}{WEBHOOK_PATH}"


@api.on_event("startup")
async def on_startup():
    await application.initialize()

    webhook_url = get_webhook_url()

    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(webhook_url)

    log.info(f"{MERCHANT_NAME} Bot started")
    log.info(f"Webhook set to: {webhook_url}")


@api.on_event("shutdown")
async def on_shutdown():
    await application.shutdown()


@api.get("/")
async def root():
    return {"status": "Pay0 bot running (auto webhook)"}


@api.get("/health")
async def health():
    return {"ok": True}


@api.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)

    await application.process_update(update)
    return {"ok": True}
