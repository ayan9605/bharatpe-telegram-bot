# Pay0 Telegram Payment Bot

UPI payment bot for Telegram — accepts payments via BharatPe with auto-verification. QR codes generated and sent directly in chat.

## Features

- **Inline buttons** — no commands needed, fully button-driven
- **Auto-verification** — polls BharatPe API, matches by micro-amount + timestamp
- **Branded QR** — generated locally with merchant name and amount
- **PostgreSQL** — persistent payment history, user stats, activity logs
- **Admin panel** — dashboard, member management, search, block/unblock, broadcast
- **Rate limiting** — max 3 concurrent + 10/hour per user
- **Middleware** — user tracking, blocked check, rate limit on every action

## Setup

```bash
# 1. Clone
git clone <repo-url>
cd telegram-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create PostgreSQL database
createdb pay0_bot

# 4. Configure
cp .env.example .env
# Edit .env with your credentials

# 5. Run
python bot.py
```

## Configuration

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `ADMIN_IDS` | Comma-separated Telegram user IDs |
| `MERCHANT_ID` | BharatPe merchant ID |
| `API_TOKEN` | BharatPe access token |
| `API_COOKIE` | BharatPe session cookie |
| `UPI_ID` | BharatPe UPI ID |
| `DATABASE_URL` | PostgreSQL connection string |
| `MERCHANT_NAME` | Display name in bot messages |

## Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/start` | All | Main menu with pay buttons |
| `/pay <amount>` | All | Quick pay with amount |
| `/admin` | Admin | Admin panel |

## Project Structure

```
├── bot.py              # Entry point
├── config.py           # Environment-based config
├── database.py         # PostgreSQL layer
├── bharatpe.py         # BharatPe transaction API
├── qr_generator.py     # Branded UPI QR codes
├── session.py          # Session helpers
└── handlers/
    ├── keyboards.py    # Button layouts
    ├── middleware.py    # Auth, rate limit, tracking
    ├── member.py       # /start, history, stats, help
    ├── payment.py      # Payment flow + BharatPe polling
    └── admin.py        # Dashboard, members, broadcast
```

## How Payment Verification Works

1. Bot generates a unique micro-amount (e.g. ₹100.03)
2. QR code with that exact amount is sent in chat
3. User scans and pays via any UPI app
4. Bot polls BharatPe transaction API every 4 seconds
5. Matches transaction by exact amount + timestamp window
6. No UTR input needed — fully automatic
