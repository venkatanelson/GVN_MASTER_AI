import os
import sqlite3
import base64
from cryptography.fernet import Fernet

def check_db_details():
    print("🔍 Checking Database Entries (Masked for Security)...")
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
            print("❌ No data found in database!")
            return

        cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
        
        uid = row[0]
        vc = cipher.decrypt(row[1]).decode() if row[1] else "NONE"
        pwd = cipher.decrypt(row[2]).decode() if row[2] else "NONE"
        app_key = cipher.decrypt(row[3]).decode() if row[3] else "NONE"
        totp_key = cipher.decrypt(row[4]).decode() if row[4] else "NONE"
        
        print(f"👤 Client ID: {uid}")
        print(f"🔑 Password Starts With: {pwd[:3]}***")
        print(f"📡 VC Starts With: {vc[:4]}***")
        print(f"🛠️ App Key Starts With: {app_key[:5]}***")
        print(f"🔢 TOTP Key Starts With: {totp_key[:5]}***")
        
        if len(app_key) < 10:
            print("⚠️ WARNING: App Key seems too short. It should be a long hex string from Shoonya Portal.")
            
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    check_db_details()
