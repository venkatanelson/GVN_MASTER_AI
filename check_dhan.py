import sqlite3
import os
import base64
from dhanhq import dhanhq
from cryptography.fernet import Fernet

# Correct database path
db_path = 'instance/gvn_algo_pro.db'

# Encryption logic from app.py
static_32_byte_string = b'gvn_secure_key_for_encryption_26'
fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
cipher = Fernet(ENCRYPTION_KEY)

def check_dhan_from_db():
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT client_id, encrypted_access_token FROM user_broker_config LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            print("❌ No Dhan configuration found in the database.")
            return

        client_id, encrypted_token = row
        access_token = cipher.decrypt(encrypted_token).decode()
        
        print(f"Connecting to Dhan with Client ID: {client_id}...")
        dhan = dhanhq(client_id, access_token)
        
        # Using get_fund_limits instead of get_profile to test connection
        funds = dhan.get_fund_limits()
        
        if funds.get('status') == 'success':
            data = funds.get('data', {})
            print("------------------------------------------")
            print(f"✅ DHAN CONNECTION SUCCESSFUL!")
            print(f"💰 Available Balance: ₹{data.get('availabelBalance', 'N/A')}")
            print("------------------------------------------")
        else:
            print(f"❌ Dhan API Error: {funds.get('remarks')}")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_dhan_from_db()
