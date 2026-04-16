import requests

TELEGRAM_BOT_TOKEN = "8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs"
TELEGRAM_CHAT_ID = "1008887074"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"TELEGRAM SEND ERROR: {e}")

send_telegram_msg(f"✅ <b>GVN Algo Notification System Connected</b>\n---------------------\n🔹 <b>Status</b>: Active\n🔹 <b>Message</b>: This is a test alert to confirm that your new Bot Token is working perfectly.\n---------------------\n⚡ <i>GVN Algo Backend</i>")
