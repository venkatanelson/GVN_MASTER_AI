"""
GVN Shoonya Login Diagnostic
Run this to test Shoonya login directly and see exact error.
"""
import sqlite3
import base64
import requests
import json
from cryptography.fernet import Fernet

# --- Load credentials from DB ---
static_key = b'gvn_secure_key_for_encryption_26'
cipher = Fernet(base64.urlsafe_b64encode(static_key))

db_path = 'instance/gvn_algo_pro.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT client_id, encrypted_access_token, encrypted_password,
           encrypted_client_secret, encrypted_totp_key, broker_name
    FROM user_broker_config LIMIT 1
""")
row = cursor.fetchone()
conn.close()

if not row:
    print("❌ No broker config found in DB!")
    exit()

client_id    = row[0]
vendor_code  = cipher.decrypt(row[1]).decode() if row[1] else ""
password     = cipher.decrypt(row[2]).decode() if row[2] else ""
api_secret   = cipher.decrypt(row[3]).decode() if row[3] else ""
totp_key     = cipher.decrypt(row[4]).decode() if row[4] else ""
broker_name  = row[5]

print(f"📋 Broker      : {broker_name}")
print(f"📋 Client ID   : {client_id}")
print(f"📋 Vendor Code : {vendor_code[:6]}... (length: {len(vendor_code)})")
print(f"📋 Password    : {'*' * len(password)} (length: {len(password)})")
print(f"📋 API Secret  : {api_secret[:6]}... (length: {len(api_secret)})")
print(f"📋 TOTP Key    : {totp_key[:6]}... (length: {len(totp_key)})")
print()

if broker_name != "Shoonya":
    print(f"⚠️  Broker is '{broker_name}', not Shoonya. Change broker in Settings!")
    exit()

if not client_id or not vendor_code or not password or not api_secret:
    print("❌ Missing credentials! Please fill all fields in API Settings:")
    print("   - Client ID (Shoonya User ID)")
    print("   - Access Token field = Vendor Code")
    print("   - Client Secret field = API Secret")
    print("   - Broker Password field = Shoonya Password")
    print("   - TOTP Secret = 16-char TOTP key")
    exit()

# --- Try TOTP ---
import pyotp
if totp_key:
    totp = pyotp.TOTP(totp_key).now()
    print(f"🔐 TOTP Generated: {totp}")
else:
    totp = ""
    print("⚠️  No TOTP key — using blank TOTP")

# --- Direct HTTP Test (bypass NorenRestApiPy) ---
print("\n🔄 Testing Shoonya Login via direct HTTP...")

import hashlib

def sha256_str(s):
    return hashlib.sha256(s.encode()).hexdigest()

# Shoonya expects SHA256 of password
pwd_hash = sha256_str(password)
app_key_hash = sha256_str(f"{api_secret}|{totp}")

payload_dict = {
    "apkversion": "1.0.0",
    "uid": client_id,
    "pwd": pwd_hash,
    "factor2": totp,
    "vc": vendor_code,
    "appkey": app_key_hash,
    "imei": "abs1234",
    "source": "API"
}

jData = "jData=" + json.dumps(payload_dict)

try:
    url = "https://api.shoonya.com/NorenWClientTP/QuickAuth"
    resp = requests.post(url, data=jData, timeout=10)
    print(f"📡 HTTP Status  : {resp.status_code}")
    print(f"📡 Raw Response : {resp.text[:500]}")
    
    if resp.text:
        result = resp.json()
        if result.get('stat') == 'Ok':
            print("\n✅ ✅ ✅  SHOONYA LOGIN SUCCESSFUL!")
            print(f"   Session Token: {result.get('susertoken', 'N/A')[:20]}...")
        else:
            print(f"\n❌ Login Failed: {result}")
            print("\n👉 SOLUTION: Re-enter your Shoonya credentials in the dashboard Settings page")
    else:
        print("❌ Empty response — URL might be wrong or server is down")
        
except Exception as e:
    print(f"❌ Connection Error: {e}")
