import httpx
import json
import hashlib
import os
import sqlite3
import base64
from cryptography.fernet import Fernet
import pyotp
import asyncio

async def test_raw_shoonya():
    print("🔍 Starting RAW HTTP/2 Test (With Updated APK Version)...")
    
    # 1. Get Details from DB
    try:
        if os.path.exists('instance/gvn_algo_pro.db'):
            conn = sqlite3.connect('instance/gvn_algo_pro.db')
        else:
            conn = sqlite3.connect('gvn_algo_pro.db')
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, encrypted_access_token, encrypted_password, encrypted_client_secret, encrypted_totp_key FROM user_broker_config LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
        uid = row[0]
        vc = cipher.decrypt(row[1]).decode() if row[1] else uid
        pwd = cipher.decrypt(row[2]).decode() if row[2] else "Gvn@12"
        app_key = cipher.decrypt(row[3]).decode() if row[3] else ""
        totp_raw = cipher.decrypt(row[4]).decode() if row[4] else "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
        
        # Prepare TOTP
        totp_clean = "".join(c for c in totp_raw if c.isalnum()).upper()
        if "FA440429" in totp_clean: totp_clean = "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
        token = pyotp.TOTP(totp_clean).now()

        # Try api.shoonya.com with the trailing slash
        url = "https://api.shoonya.com/NorenWSTP/QuickAuthenticate"
        
        # SHA256 of password
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        
        # Using py:0.0.22 as apkversion to match library version
        payload = {
            "apkversion": "py:0.0.22",
            "uid": uid,
            "pwd": pwd_hash,
            "factor2": token,
            "vc": vc,
            "appkey": hashlib.sha256(f"{uid}|{app_key}".encode()).hexdigest(),
            "imei": "ABC123456789",
            "source": "API"
        }
        
        print(f"📡 Sending HTTP/2 Request to: {url}")
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            response = await client.post(url, data={"jData": json.dumps(payload)}, headers=headers)
            
            print(f"📥 HTTP Status Code: {response.status_code}")
            print(f"📥 RAW Response Body: '{response.text}'")
            
            if response.text:
                try:
                    res_json = response.json()
                    print(f"✅ Parsed JSON: {res_json}")
                except:
                    print("❌ Response is not valid JSON.")
            else:
                print("❌ Response is empty!")

    except Exception as e:
        print(f"💥 TEST ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_raw_shoonya())
