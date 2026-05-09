import sqlite3
import os

# GVN Master DB Fix Script - Adds ALL missing columns
db_path = 'instance/gvn_algo_pro.db'

if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}. Please run app.py once first.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # ─── user_broker_config columns ───
        cursor.execute("PRAGMA table_info(user_broker_config)")
        broker_cols = [col[1] for col in cursor.fetchall()]
        print(f"📋 Current user_broker_config columns: {broker_cols}")

        broker_additions = [
            ("call_strike",              "VARCHAR(50)"),
            ("put_strike",               "VARCHAR(50)"),
            ("client_id",                "VARCHAR(100)"),
            ("encrypted_access_token",   "BLOB"),
            ("encrypted_client_secret",  "BLOB"),
            ("encrypted_totp_key",       "BLOB"),
            ("encrypted_password",       "BLOB"),
        ]
        for col_name, col_type in broker_additions:
            if col_name not in broker_cols:
                try:
                    cursor.execute(f"ALTER TABLE user_broker_config ADD COLUMN {col_name} {col_type}")
                    conn.commit()
                    print(f"✅ Added '{col_name}' to user_broker_config")
                except Exception as e:
                    print(f"⚠️  Could not add '{col_name}': {e}")
            else:
                print(f"ℹ️  '{col_name}' already exists in user_broker_config")

        # ─── algo_trades_v3 columns ───
        cursor.execute("PRAGMA table_info(algo_trades_v3)")
        trade_cols = [col[1] for col in cursor.fetchall()]
        print(f"\n📋 Current algo_trades_v3 columns: {trade_cols}")

        trade_additions = [
            ("target_price", "FLOAT"),
            ("stop_loss",    "FLOAT"),
            ("ai_opinion",   "VARCHAR(500)"),
            ("user_id",      "INTEGER"),
        ]
        for col_name, col_type in trade_additions:
            if col_name not in trade_cols:
                try:
                    cursor.execute(f"ALTER TABLE algo_trades_v3 ADD COLUMN {col_name} {col_type}")
                    conn.commit()
                    print(f"✅ Added '{col_name}' to algo_trades_v3")
                except Exception as e:
                    print(f"⚠️  Could not add '{col_name}': {e}")
            else:
                print(f"ℹ️  '{col_name}' already exists in algo_trades_v3")

        # ─── user table columns ───
        cursor.execute('PRAGMA table_info("user")')
        user_cols = [col[1] for col in cursor.fetchall()]
        print(f"\n📋 Current user columns: {user_cols}")

        user_additions = [
            ("is_blocked",             "BOOLEAN DEFAULT 0"),
            ("is_admin",               "BOOLEAN DEFAULT 0"),
            ("is_locked",              "BOOLEAN DEFAULT 1"),
            ("signals_unlocked_until", "TIMESTAMP"),
            ("full_auto_mode",         "BOOLEAN DEFAULT 0"),
            ("trade_lots",             "INTEGER DEFAULT 1"),
            ("personal_discount",      "INTEGER DEFAULT 0"),
        ]
        for col_name, col_type in user_additions:
            if col_name not in user_cols:
                try:
                    cursor.execute(f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type}')
                    conn.commit()
                    print(f"✅ Added '{col_name}' to user table")
                except Exception as e:
                    print(f"⚠️  Could not add '{col_name}': {e}")
            else:
                print(f"ℹ️  '{col_name}' already exists in user table")

        conn.close()
        print("\n✅ ✅ ✅  GVN Database Fix Complete! Now run: python app.py")

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
