import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1008887074")

def send_telegram_msg(message):
    base_api = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org").rstrip('/')
    url = f"{base_api}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    proxy_url = os.environ.get("TELEGRAM_PROXY")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    try:
        response = requests.post(url, json=payload, proxies=proxies, timeout=10)
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"TELEGRAM SEND ERROR: {e}")

send_telegram_msg(f"✅ <b>GVN Algo Notification System Connected</b>\n---------------------\n🔹 <b>Status</b>: Active\n🔹 <b>Message</b>: This is a test alert to confirm that your new Bot Token is working perfectly.\n---------------------\n⚡ <i>GVN Algo Backend</i>")
