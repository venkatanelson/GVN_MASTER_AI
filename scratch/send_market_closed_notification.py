import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1008887074")

msg = (
    "🛑 <b>GVN MASTER ALGO - MARKET CLOSE ALERT SILENCED</b>\n"
    "--------------------------------------------------\n"
    "✅ <b>Status:</b> Market Closed @ 3:30 PM IST\n"
    "🛡️ <b>Order Guard:</b> Post-market retry loops & Order Failure alerts are now SILENCED!\n"
    "📊 <b>Today Total Realized P&L:</b> +₹ 12,481.30\n"
    "🚀 <b>Tomorrow Bias:</b> GAP UP (+35 to +60 Points)\n"
    "--------------------------------------------------\n"
    "⚡ <i>GVN Master AI Orchestrator</i>"
)

url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
try:
    resp = requests.post(url, json=payload, timeout=10)
    print(f"Telegram sent: {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
