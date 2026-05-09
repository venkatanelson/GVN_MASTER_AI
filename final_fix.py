import os
import sqlite3
import base64
from cryptography.fernet import Fernet

def force_fix_database():
    print("🚀 [GVN ALGO] Starting Ultimate Force Fix...")
    
    # Correct Details
    UID = "FA440429_U"
    PWD = "Gvn@12"
    VC = "FA440429_U" # For Shoonya, VC is usually the UserID
    APP_KEY = "Hjh4nR9yXnn4xF9i4ALKrj1AaZyJ4hlIlChq5HHo4qXX9HOXNhdlhNCGXigRJ4d4"
    TOTP_KEY = "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
    
    try:
        # Determine DB path
        db_path = 'instance/gvn_algo_pro.db' if os.path.exists('instance/gvn_algo_pro.db') else 'gvn_algo_pro.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_broker_config'")
        if not cursor.fetchone():
            print("❌ Table 'user_broker_config' not found! Please run app.py first to create the DB.")
            return

        # Encryption
        cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
        
        enc_pwd = cipher.encrypt(PWD.encode())
        enc_vc = cipher.encrypt(VC.encode())
        enc_app = cipher.encrypt(APP_KEY.encode())
        enc_totp = cipher.encrypt(TOTP_KEY.encode())
        
        # Update Database
        cursor.execute("""
            UPDATE user_broker_config 
            SET client_id = ?, 
                encrypted_access_token = ?, 
                encrypted_password = ?, 
                encrypted_client_secret = ?, 
                encrypted_totp_key = ?,
                broker_name = 'Shoonya'
            WHERE id = 1
        """, (UID, enc_vc, enc_pwd, enc_app, enc_totp))
        
        # If no row exists, insert one
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO user_broker_config (id, client_id, encrypted_access_token, encrypted_password, encrypted_client_secret, encrypted_totp_key, broker_name)
                VALUES (1, ?, ?, ?, ?, ?, 'Shoonya')
            """, (UID, enc_vc, enc_pwd, enc_app, enc_totp))
            
        conn.commit()
        conn.close()
        print("✅ DATABASE FIXED SUCCESSFULLY! All credentials are now correct.")
        
    except Exception as e:
        print(f"💥 FIX ERROR: {e}")

if __name__ == "__main__":
    force_fix_database()
