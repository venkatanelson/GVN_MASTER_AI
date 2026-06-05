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
        "text": "🤖 <b>GVN ALGO DIAGNOSTIC:</b> Authentication Successful! Telegram integration is perfectly configured.",
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"✅ TELEGRAM SUCCESS: Message delivered successfully.")
        else:
            print(f"⚠️ TELEGRAM WARNING: Channel post failed. Trying direct chat...")
            payload["chat_id"] = TELEGRAM_CHAT_ID
            res2 = requests.post(url, json=payload, timeout=5)
            if res2.status_code == 200:
                print(f"✅ TELEGRAM SUCCESS: Message delivered to private chat.")
    except Exception as e:
        print(f"❌ TELEGRAM ERROR: {e}")

test_telegram()

# 2. TEST DATABASE & SHOONYA API KEY STATUS
print("\n[2] CHECKING SHOONYA API SETUP IN DATABASE...")
with app.app_context():
    config = UserBrokerConfig.query.first()
    if not config:
        print("❌ DATABASE WARNING: No Broker Configuration found!")
    else:
        print(f"✅ Active Broker Selected: {config.broker_name}")
        print(f"✅ Client ID: {config.client_id}")
        
        # Check Access Token
        if config.api_key:
            print("✅ Access Token (VC): SAVED")
            vc = config.api_key
        else:
            print("❌ Access Token (VC): MISSING")
            vc = ""
            
        # Check API Secret
        if config.api_secret:
            print("✅ API Secret: SAVED")
            sec = config.api_secret
        else:
            print("❌ API Secret: MISSING")
            sec = ""

        # Check TOTP Key
        if config.totp_key:
            print("✅ TOTP Key: SAVED")
            t_key = config.totp_key
        else:
            print("❌ TOTP Key: MISSING")
            t_key = ""

        # Check Password
        if config.encrypted_password:
            print("✅ Broker Password: SAVED")
            pwd = cipher.decrypt(config.encrypted_password).decode()
        else:
            print("✅ Broker Password: USING DEFAULT (Gvn@12)")
            pwd = "Gvn@12"

        # 🌟 Sync to local feed test if needed (Bypassed in diagnostics)
        pass

# 3. TEST OPTION CHAIN DATA FETCHING
print("\n[3] CHECKING OPTION CHAIN DATA (NSE ENGINE)...")
try:
    print(f"📡 Requesting live NIFTY Option Chain data at {datetime.now().strftime('%H:%M:%S')}...")
    import nse_option_chain
    import shared_data
    nse_option_chain.analyze_and_update_gvn_scanner("NIFTY")
    last_upd = shared_data.gvn_scanner_data.get("last_updated")
    
    if last_upd:
        print(f"✅ DATA SUCCESS: Successfully fetched Option Chain data! Last Updated: {last_upd}")
        sample = shared_data.gvn_scanner_data.get("NIFTY", [])
        if sample:
            print(f"📊 Live Market Pulse: Data found.")
    else:
        print("❌ DATA FAILURE: The NSE Engine is not returning any data.")
        print("💡 TIP: Check nse_status.log for login/connection logs.")
except Exception as e:
    print(f"❌ DATA CRASH: {e}")

print("\n" + "="*50)
print("🏁 DIAGNOSTIC COMPLETE")
print("="*50)
