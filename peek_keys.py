
import sqlite3
import base64
from cryptography.fernet import Fernet

def peek_keys():
    static_key = b'gvn_secure_key_for_encryption_26'
    cipher = Fernet(base64.urlsafe_b64encode(static_key))
    
    def decrypt(val):
        if not val: return ""
        try: return cipher.decrypt(val).decode()
        except: return str(val)

    db_path = 'instance/gvn_algo_pro.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT broker_name, client_id, api_key, api_secret, totp_key, encrypted_password FROM user_broker_config")
        rows = cursor.fetchall()
        print("\n--- DATABASE CREDENTIALS ---")
        for row in rows:
            print(f"Broker: {row[0]}")
            print(f"Client ID: {row[1]}")
            print(f"API Key: {row[2]}")
            print(f"TOTP Key: {row[4]}")
            print(f"Password: {decrypt(row[5])}")
            print("-" * 20)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    peek_keys()
