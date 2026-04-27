import os
import requests
import json
from app import app, db, UserBrokerConfig, cipher
import shoonya_live_feed
from datetime import datetime

print("="*50)
print("🔍 GVN ALGO FULL DIAGNOSTIC TOOL 🚀")
print("="*50)

# 1. TEST TELEGRAM AUTHENTICATION
print("\n[1] CHECKING TELEGRAM AUTHENTICATION...")
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '@indicator_Gvn')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '1008887074')

def test_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": "🤖 <b>GVN ALGO DIAGNOSTIC:</b> Authentication Successful! Telegram integration is perfectly configured. No fake alerts detected.",
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"✅ TELEGRAM SUCCESS: Message delivered successfully to channel {TELEGRAM_CHANNEL_ID}.")
        else:
            print(f"⚠️ TELEGRAM WARNING: Channel post failed (Code {res.status_code}). Reason: {res.text}")
            print(f"-> Trying direct chat ID {TELEGRAM_CHAT_ID} instead...")
            payload["chat_id"] = TELEGRAM_CHAT_ID
            res2 = requests.post(url, json=payload, timeout=5)
            if res2.status_code == 200:
                print(f"✅ TELEGRAM SUCCESS: Message delivered successfully to private chat {TELEGRAM_CHAT_ID}.")
            else:
                print(f"❌ TELEGRAM ERROR: {res2.text}")
    except Exception as e:
        print(f"❌ TELEGRAM ERROR: {e}")

test_telegram()

# 2. TEST DATABASE & SHOONYA API KEY STATUS
print("\n[2] CHECKING SHOONYA API SETUP IN DATABASE...")
with app.app_context():
    config = UserBrokerConfig.query.first()
    if not config:
        print("❌ DATABASE WARNING: No Broker Configuration found in the database. You haven't saved keys in the dashboard!")
    else:
        print(f"✅ Active Broker Selected: {config.broker_name}")
        print(f"✅ Client ID: {config.client_id}")
        
        # Check if keys are saved (encrypted)
        if config.encrypted_access_token:
            print("✅ Access Token: SAVED & ENCRYPTED")
        else:
            print("❌ Access Token: MISSING")
            
        if config.encrypted_password:
            print("✅ Broker Password (Shoonya): SAVED & ENCRYPTED")
        else:
            print("⚠️ Broker Password (Shoonya): MISSING (Only required for Shoonya)")

# 3. TEST OPTION CHAIN DATA FETCHING
print("\n[3] CHECKING OPTION CHAIN DATA (NSE ENGINE)...")
try:
    print(f"📡 Requesting live NIFTY Option Chain data at {datetime.now().strftime('%H:%M:%S')}...")
    shoonya_live_feed.analyze_and_update_gvn_scanner("NIFTY")
    last_upd = shoonya_live_feed.gvn_scanner_data.get("last_updated")
    
    if last_upd:
        print(f"✅ DATA SUCCESS: Successfully fetched Option Chain data! Last Updated: {last_upd}")
        sample = shoonya_live_feed.gvn_scanner_data.get("NIFTY", [])
        if sample:
            print(f"📊 Live Market Pulse (CE/PE Strikes Available): {len(sample)}")
            print(f"🔍 Sample Data (Top Strike): Strike {sample[0].get('strike')} | LTP: ₹{sample[0].get('ltp')} | OI: {sample[0].get('oi')}")
        else:
            print("⚠️ Data fetched but NIFTY list is empty.")
    else:
        print("❌ DATA FAILURE: The Shoonya Engine is not returning any data. Please check Shoonya Login/Password in Dashboard.")
except Exception as e:
    print(f"❌ DATA CRASH: Error fetching Option Chain -> {e}")

print("\n" + "="*50)
print("🏁 DIAGNOSTIC COMPLETE")
print("="*50)
