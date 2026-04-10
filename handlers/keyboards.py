"""Shared keyboard layouts."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_IDS


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def home_kb(uid: int = 0):
    rows = [
        [InlineKeyboardButton("💳 Pay Now", callback_data="pay:start")],
        [
            InlineKeyboardButton("₹10", callback_data="pay:10"),
            InlineKeyboardButton("₹50", callback_data="pay:50"),
            InlineKeyboardButton("₹100", callback_data="pay:100"),
            InlineKeyboardButton("₹500", callback_data="pay:500"),
        ],
        [
            InlineKeyboardButton("📋 History", callback_data="me:history"),
            InlineKeyboardButton("📊 Stats", callback_data="me:stats"),
            InlineKeyboardButton("ℹ️ Help", callback_data="me:help"),
        ],
    ]
    if is_admin(uid):
        rows.append([InlineKeyboardButton("🔐 Admin", callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)


def amounts_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("₹10", callback_data="pay:10"),
            InlineKeyboardButton("₹50", callback_data="pay:50"),
            InlineKeyboardButton("₹100", callback_data="pay:100"),
        ],
        [
            InlineKeyboardButton("₹500", callback_data="pay:500"),
            InlineKeyboardButton("₹1000", callback_data="pay:1000"),
            InlineKeyboardButton("₹2000", callback_data="pay:2000"),
        ],
        [InlineKeyboardButton("✏️ Custom", callback_data="pay:custom")],
    ])


def waiting_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel Payment", callback_data="pay:cancel")],
    ])


def result_kb(uid: int = 0):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay Again", callback_data="pay:start")],
        [InlineKeyboardButton("🏠 Menu", callback_data="nav:home")],
    ])


def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin:dash")],
        [InlineKeyboardButton("💰 Recent", callback_data="admin:recent"),
         InlineKeyboardButton("👥 Members", callback_data="admin:users")],
        [InlineKeyboardButton("🔍 Search", callback_data="admin:search")],
        [InlineKeyboardButton("🚫 Block", callback_data="admin:block"),
         InlineKeyboardButton("✅ Unblock", callback_data="admin:unblock")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("🏠 Menu", callback_data="nav:home")],
    ])


def back_admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back", callback_data="admin:panel")],
    ])
