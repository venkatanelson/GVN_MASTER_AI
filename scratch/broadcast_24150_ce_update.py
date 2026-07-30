import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1008887074")

# Telegram Channel broadcast message
tg_msg = (
    "🚀 <b>GVN MASTER ALGO - LIVE TREND CONFIRMATION ALERT</b>\n"
    "--------------------------------------------------\n"
    "🔥 <b>Strike: NIFTY 24150 CE</b>\n"
    "📍 <b>Price Action:</b> Rebound from ₹150 (i6 Level Hold)\n"
    "📊 <b>Formula 5 (RSI-50 Gravity Retracement):</b> Confirmed RSI 54 Support Bounce\n"
    "⚡ <b>Breakout Status:</b> Crossed & Holding above ₹178.63 (i5 Level)\n"
    "🎯 <b>Immediate Target 1 (i3 / 0.786):</b> ₹211.91\n"
    "🚀 <b>Target 2 (0.2.2.2 / i2 / 0.200 Level):</b> ₹252.80 (Gamma Squeeze Squeeze Acceleration Zone)\n"
    "--------------------------------------------------\n"
    "🟢 <b>Status:</b> BUYERS MOMENTUM CONFIRMED | HOLDING TARGET TRAIL\n"
    "⚡ <i>GVN Master AI Orchestrator</i>"
)

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
        print(f"Telegram Response: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"TELEGRAM SEND ERROR: {e}")
        return False

# Send Telegram
send_telegram_msg(tg_msg)

# Update live_market_data.json for Algo User Dashboard
live_file_path = "live_market_data.json"
if os.path.exists(live_file_path):
    try:
        with open(live_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Update scanner item for 24150 CE
        if "scanner" in data and "NIFTY" in data["scanner"]:
            for item in data["scanner"]["NIFTY"]:
                if item.get("strike") == "24150 CE":
                    item["ai_signal"] = "🚀 CONFIRMED BUY: 178.63 (i5) -> 211.91 (i3 TGT1) -> 252.80 (0.2.2.2 TGT2)"
                    item["zone"] = "🚀 BULLISH BREAKOUT CONFIRMED"
                    item["pressure"] = "🔥 HIGH BUYER ACCELERATION"
                    item["potential"] = "VERY HIGH"
                    print("Updated 24150 CE in live_market_data.json scanner")
        
        # Update pulse insight
        if "pulse" in data and "NIFTY" in data["pulse"]:
            data["pulse"]["NIFTY"]["ai_insight"] = "🔥 24150 CE RSI 54 Retracement Confirmed! Target 211.91 & 0.2.2.2 (252.80) Active!"
            data["pulse"]["NIFTY"]["wind_direction_only"] = "UP / CE ACCELERATION 🟢"

        with open(live_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("Successfully updated live_market_data.json for Dashboard!")
    except Exception as e:
        print(f"Error updating live_market_data.json: {e}")
