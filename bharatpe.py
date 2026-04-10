"""
BharatPe Transaction API — fetch and match payments.
"""

import logging
import requests
from datetime import datetime, timedelta
from config import MERCHANT_ID, API_TOKEN, API_COOKIE, BHARATPE_API, USER_AGENT

logger = logging.getLogger(__name__)


def fetch_transactions() -> list:
    """Fetch recent QR payment transactions from BharatPe."""
    from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    try:
        resp = requests.get(
            BHARATPE_API,
            params={
                "module": "PAYMENT_QR",
                "merchantId": MERCHANT_ID,
                "sDate": from_date,
                "eDate": to_date,
            },
            headers={
                "token": API_TOKEN,
                "Cookie": API_COOKIE,
                "User-Agent": USER_AGENT,
            },
            timeout=15,
        )
        data = resp.json()

        if data.get("status") and data.get("message") == "SUCCESS":
            txns = data.get("data", {}).get("transactions", [])
            logger.info(f"BharatPe: {len(txns)} transactions fetched")
            return txns

        logger.warning(f"BharatPe API error: {data.get('message')} | HTTP {resp.status_code}")
        return []

    except requests.RequestException as e:
        logger.error(f"BharatPe API failed: {e}")
        return []


def find_payment(amount: float, created_at: datetime, expire_at: datetime) -> dict | None:
    """
    Find a matching BharatPe transaction by:
    - amount ± ₹0.001
    - type = PAYMENT_RECV, status = SUCCESS
    - timestamp within [created_at, expire_at] window

    Returns dict with amount, utr, timestamp, vpa or None.
    """
    for tx in fetch_transactions():
        if tx.get("type") != "PAYMENT_RECV" or tx.get("status") != "SUCCESS":
            continue

        tx_amount = float(tx.get("amount", 0))
        tx_ms = int(tx.get("paymentTimestamp", 0))
        tx_time = datetime.fromtimestamp(tx_ms / 1000)

        if abs(tx_amount - amount) < 0.001 and created_at <= tx_time <= expire_at:
            return {
                "amount": tx_amount,
                "utr": tx.get("bankReferenceNo", ""),
                "timestamp": tx_time.strftime("%Y-%m-%d %H:%M:%S"),
                "vpa": tx.get("payerVpa", ""),
            }

    return None
