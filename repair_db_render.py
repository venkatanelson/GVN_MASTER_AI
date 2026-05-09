
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def repair_database():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in environment!")
        return

    # Fix for postgres:// vs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print(f"📡 Connecting to Render Database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        # List of columns to add to 'user' table
        user_columns = [
            ("password_hash", "VARCHAR(128)"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("is_admin", "BOOLEAN DEFAULT FALSE"),
            ("dhan_webhook_url", "VARCHAR(500)"),
            ("selected_plan", "VARCHAR(50) DEFAULT 'Basic'"),
            ("admin_kill_switch", "BOOLEAN DEFAULT FALSE"),
            ("user_type", "VARCHAR(20) DEFAULT 'LIVE'"),
            ("is_approved", "BOOLEAN DEFAULT TRUE"),
            ("is_locked", "BOOLEAN DEFAULT FALSE"),
            ("trade_lots", "INTEGER DEFAULT 1"),
            ("demo_capital", "FLOAT DEFAULT 100000.0"),
            ("expiry_date", "TIMESTAMP")
        ]

        print("🛠️ Checking and adding missing columns to 'user' table...")
        for col_name, col_type in user_columns:
            try:
                cursor.execute(f"ALTER TABLE \"user\" ADD COLUMN {col_name} {col_type};")
                print(f"✅ Added column: {col_name}")
            except psycopg2.errors.DuplicateColumn:
                print(f"ℹ️ Column already exists: {col_name}")
            except Exception as e:
                print(f"⚠️ Error adding {col_name}: {e}")

        print("🎉 Database Repair Complete!")
        conn.close()
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    repair_database()
