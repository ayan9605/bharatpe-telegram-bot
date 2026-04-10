"""Pay0 Telegram Bot — Configuration"""

import os

# ── Telegram ───────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ── Admin ──────────────────────────────────────────────
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "2089273221").split(",") if x.strip()]

# ── BharatPe ───────────────────────────────────────────
MERCHANT_ID = os.getenv("MERCHANT_ID", "30549438")
API_TOKEN = os.getenv("API_TOKEN", "ea46cc77dcea44d1b84d61fb7e3d0e35")
API_COOKIE = os.getenv("API_COOKIE",
    "eyJpdiI6ImhvMlR4SmhQQXdISTNwRVoxZTRvNVE9PSIsInZhbHVlIjoiRnE5a1VkRVA2dlRy"
    "QXgybzlOXC9LWWF6VUg5QWxiVEdxN3h3ZWFYQllZUzFxZFwvZ1ZVNnNqZFY1Z1BBaEhpcUlG"
    "WWl5ZzRpa044ZVd5dWcrQ0hYSjk5T3AwY2RMVWQ1R1pvcVBLUmdRU09BbHlhV2lkNmdKM2hH"
    "ZmJQUm00ajNOKyIsIm1hYyI6IjUyMjA4NzNmYzYwZGNjYTM1ZTg2ODNkNGM3MDkyYTM2NjBi"
    "NmIwZGVkMjI4YTE3ZjYxZmRhNDRiZGQzODdhNzAifQ%3D%3D"
)
UPI_ID = os.getenv("UPI_ID", "BHARATPE09917537019@yesbankltd")

# ── PostgreSQL ─────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pay0_bot")

# ── Payment ────────────────────────────────────────────
MERCHANT_NAME = os.getenv("MERCHANT_NAME", "Tamil Digital")
TIMEOUT = 300       # 5 min
POLL_INTERVAL = 4   # seconds
MIN_AMOUNT = 1
MAX_AMOUNT = 50000

# ── Rate Limit ─────────────────────────────────────────
MAX_PAYMENTS_PER_HOUR = 10
MAX_CONCURRENT_PAYMENTS = 3

# ── BharatPe API ───────────────────────────────────────
BHARATPE_API = "https://payments-tesseract.bharatpe.in/api/v1/merchant/transactions"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
)
