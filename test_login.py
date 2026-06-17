import os
import sqlite3
import base64
from cryptography.fernet import Fernet
import pyotp
from NorenRestApiPy.NorenApi import NorenApi

def test_shoonya():
    print("[TEST] Testing Shoonya Login Details...")
    
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
        
        if not row:
            print("[ERROR] No Shoonya config found in database!")
            return

        cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
        uid = row[0]
        vc = cipher.decrypt(row[1]).decode() if row[1] else uid
        pwd = cipher.decrypt(row[2]).decode() if row[2] else "Gvn@12"
        app_key = cipher.decrypt(row[3]).decode() if row[3] else ""
        totp_raw = cipher.decrypt(row[4]).decode() if row[4] else "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
        
        print(f"[INFO] Client ID: {uid}")
        print(f"[INFO] VC: {'SAVED' if vc else 'MISSING'}")
        print(f"[INFO] App Key: {'SAVED' if app_key else 'MISSING'}")
        
        # 2. Generate TOTP
        try:
            totp_clean = "".join(c for c in totp_raw if c.isalnum()).upper()
            if "FA440429" in totp_clean: totp_clean = "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
            token = pyotp.TOTP(totp_clean).now()
            print(f"[INFO] TOTP Token Generated: {token}")
        except Exception as e:
            print(f"[ERROR] TOTP Generation Failed: {e}")
            return

        # 3. Attempt Login
        class ShoonyaApiPy(NorenApi):
            def __init__(self):
                NorenApi.__init__(self, host='https://api.shoonya.com/NorenWSTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        
        api = ShoonyaApiPy()
        print("[INFO] Sending login request to Shoonya...")
        
        ret = api.login(userid=uid, password=pwd, twoFA=token, vendor_code=vc, api_secret=app_key, imei='ABC123456789')
        
        if ret:
            print(f"[INFO] Response received: {ret}")
            if ret.get('stat') == 'Ok':
                print("[SUCCESS] Login is working perfectly.")
            else:
                print(f"[WARNING] LOGIN FAILED: {ret.get('emsg', 'Unknown Error')}")
        else:
            print("[ERROR] SERVER RETURNED EMPTY RESPONSE.")

    except Exception as e:
        print(f"[CRASH] CRASH DURING TEST: {e}")

if __name__ == "__main__":
    test_shoonya()
