import sys
import pyotp
import hashlib
import json
import requests
from NorenRestApiPy.NorenApi import NorenApi

def get_totp(totp_key):
    try:
        return pyotp.TOTP(totp_key).now()
    except Exception as e:
        print(f"❌ TOTP Generation Error: {e}")
        return ""

def sha256_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

def test_login():
    print("📡 GVN SHOONYA CONNECTION DIAGNOSTICS")
    print("====================================")
    
    # Credentials from screenshot
    client_id    = "FA440429_U"
    password     = "Kalavathi@12"
    vendor_code  = "venkata"
    api_secret   = "Hjh4nR9yXnn4xF9I4ALKrJ1AaZyj4hIlChq5HHo4qXX9HOXNhdIhNCGXIgRj4d4"
    totp_key     = "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
    
    totp = get_totp(totp_key)
    print(f"🔑 Generated TOTP Pin: {totp} (from key: {totp_key[:5]}...)")
    
    # Try Official NorenApi
    try:
        print("\n🔄 Strategy 1: Attempting Official NorenApi Login...")
        api = NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        ret = api.login(userid=client_id, password=password, twoFA=totp, 
                        vendor_code=vendor_code, api_secret=api_secret, imei="abc1234")
        print(f"💬 Shoonya Official API Response: {ret}")
        if ret and ret.get('stat') == 'Ok':
            print("✅ SUCCESS! Connected perfectly via official API.")
            return
    except Exception as e:
        print(f"❌ Official API Library Crash: {e}")

    # Try Direct HTTP Call
    try:
        print("\n🔄 Strategy 2: Attempting Direct HTTP QuickAuth Fallback...")
        pwd_hash = sha256_hash(password)
        app_key_hash = sha256_hash(f"{client_id}|{api_secret}")
        payload = {
            "apkversion": "1.0.0",
            "uid": client_id,
            "pwd": pwd_hash,
            "twofa": totp,
            "vc": vendor_code,
            "appkey": app_key_hash,
            "imei": "abc1234",
            "source": "API"
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        jData = "jData=" + json.dumps(payload)
        resp = requests.post("https://api.shoonya.com/NorenWClientTP/QuickAuth", data=jData, headers=headers, timeout=10)
        print(f"🌐 HTTP Status Code: {resp.status_code}")
        print(f"💬 Direct HTTP API Response: {resp.text}")
    except Exception as e:
        print(f"❌ Direct HTTP Call Failed: {e}")

if __name__ == "__main__":
    test_login()
