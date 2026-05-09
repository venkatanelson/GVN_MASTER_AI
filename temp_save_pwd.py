import os
import base64
from cryptography.fernet import Fernet
import sqlite3

# 1. Setup Encryption
static_32_byte_string = b'gvn_secure_key_for_encryption_26'
fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
cipher = Fernet(ENCRYPTION_KEY)

# 2. Encrypt Password
password = "Gvn@12"
encrypted_pwd = cipher.encrypt(password.encode())

# 3. Update Database (SQLite)
try:
    db_path = 'instance/gvn_algo_pro.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure column exists (Emergency check)
        try:
            cursor.execute("ALTER TABLE user_broker_config ADD COLUMN encrypted_password BLOB")
        except:
            pass
            
        # Update first row or all rows for Gvn
        cursor.execute("UPDATE user_broker_config SET encrypted_password = ?, broker_name = 'Shoonya'", (encrypted_pwd,))
        conn.commit()
        print(f"✅ Success: Shoonya Password ('Gvn@12') encrypted and saved to SQLite.")
        conn.close()
    else:
        print("❌ Error: SQLite database file not found at instance/gvn_algo_pro.db")
except Exception as e:
    print(f"❌ Error updating SQLite: {e}")

# 4. Update Database (Postgres if exists)
db_url = os.environ.get('DATABASE_URL')
if db_url:
    try:
        import psycopg2
        conn = psycopg2.connect(db_url.replace("postgres://", "postgresql://", 1))
        cursor = conn.cursor()
        cursor.execute("UPDATE user_broker_config SET encrypted_password = %s, broker_name = 'Shoonya'", (encrypted_pwd,))
        conn.commit()
        print("✅ Success: Shoonya Password encrypted and saved to Postgres.")
        conn.close()
    except Exception as e:
        print(f"❌ Error updating Postgres: {e}")
