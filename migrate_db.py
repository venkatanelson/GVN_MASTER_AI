
import sqlite3
import os

db_path = 'gvn_algo_pro.db'

def migrate():
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"🔍 Starting migration for {db_path}...")
    
    try:
        # Add password_hash
        cursor.execute("ALTER TABLE user ADD COLUMN password_hash VARCHAR(128)")
        print("✅ Added column: password_hash")
    except sqlite3.OperationalError:
        print("ℹ️ Column password_hash already exists.")

    try:
        # Add role
        cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
        print("✅ Added column: role")
    except sqlite3.OperationalError:
        print("ℹ️ Column role already exists.")

    try:
        # Add is_active
        cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("✅ Added column: is_active")
    except sqlite3.OperationalError:
        print("ℹ️ Column is_active already exists.")

    conn.commit()
    conn.close()
    print("🚀 Migration Complete! You can now run app.py")

if __name__ == "__main__":
    migrate()
