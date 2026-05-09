import sqlite3
import base64
from cryptography.fernet import Fernet
import os

def recover_data():
    static_key = b'gvn_secure_key_for_encryption_26'
    cipher = Fernet(base64.urlsafe_b64encode(static_key))
    
    def decrypt(val):
        if not val: return ""
        try: return cipher.decrypt(val).decode()
        except: return ""
    
    old_dbs = ['instance/gvn_master_algo.db', 'instance/gvn_master_v1.db']
    new_db = 'instance/gvn_algo_pro.db'
    
    found_config = None
    
    for db_path in old_dbs:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_broker_config WHERE user_id = 1")
                row = cursor.fetchone()
                if row:
                    cursor.execute("PRAGMA table_info(user_broker_config)")
                    cols = [c[1] for c in cursor.fetchall()]
                    config = dict(zip(cols, row))
                    
                    if config.get('broker_name', '').lower() in ['angelone', 'angel']:
                        print(f"✅ Found Angel One credentials in {db_path}!")
                        found_config = config
                        conn.close()
                        break
                conn.close()
            except Exception as e:
                print(f"Error reading {db_path}: {e}")
                
    if not found_config:
        print("❌ Sorry, could not find Angel One credentials in the old databases.")
        return
        
    print("\n--- RECOVERED CREDENTIALS ---")
    print(f"Broker: {found_config.get('broker_name')}")
    print(f"Client ID: {found_config.get('client_id')}")
    
    api_key = decrypt(found_config.get('encrypted_access_token'))
    api_secret = decrypt(found_config.get('encrypted_client_secret'))
    totp_key = decrypt(found_config.get('encrypted_totp_key'))
    enc_password = found_config.get('encrypted_password')
    
    if os.path.exists(new_db):
        try:
            print(f"\n🔄 Restoring to current database ({new_db})...")
            conn = sqlite3.connect(new_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM user_broker_config WHERE user_id = 1")
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE user_broker_config SET 
                    broker_name = 'AngelOne', client_id = ?, api_key = ?, api_secret = ?, 
                    totp_key = ?, encrypted_password = ?
                    WHERE user_id = 1
                """, (
                    found_config.get('client_id', ''),
                    api_key,
                    api_secret,
                    totp_key,
                    enc_password
                ))
            else:
                cursor.execute("""
                    INSERT INTO user_broker_config 
                    (user_id, broker_name, client_id, api_key, api_secret, totp_key, encrypted_password)
                    VALUES (1, 'AngelOne', ?, ?, ?, ?, ?)
                """, (
                    found_config.get('client_id', ''),
                    api_key,
                    api_secret,
                    totp_key,
                    enc_password
                ))
            conn.commit()
            conn.close()
            print("✅ SUCCESS! Angel One credentials restored completely.")
            print("▶️ Please start `python app.py` again, and you won't need to type them!")
        except Exception as e:
            print(f"❌ Failed to restore data: {e}")

if __name__ == '__main__':
    recover_data()
