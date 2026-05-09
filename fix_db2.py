import sqlite3
import os

def fix_db():
    db_path = 'instance/gvn_algo_pro.db'
    if not os.path.exists(db_path):
        db_path = 'gvn_algo_pro.db' # fallback
        
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(user_broker_config)")
    cols = [row[1] for row in cursor.fetchall()]
    
    required = [
        ("broker_name", "VARCHAR(50) DEFAULT 'Shoonya'"),
        ("api_key", "VARCHAR(200)"),
        ("api_secret", "VARCHAR(200)"),
        ("totp_key", "VARCHAR(100)"),
        ("encrypted_password", "BLOB"),
        ("client_id", "VARCHAR(100)")
    ]
    
    added_any = False
    for col_name, col_type in required:
        if col_name not in cols:
            try:
                print(f"Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE user_broker_config ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"✅ Added {col_name}")
                added_any = True
            except Exception as e:
                print(f"❌ Error adding {col_name}: {e}")
        else:
            print(f"ℹ️ Column {col_name} already exists.")
            
    conn.close()
    if added_any:
        print("Database fix complete! You can now run python app.py")
    else:
        print("All required columns already exist.")

if __name__ == '__main__':
    fix_db()
