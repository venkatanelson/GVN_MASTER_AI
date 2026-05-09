
import os
import sqlite3

db_path = 'gvn_algo_pro.db'

def repair():
    print("🚀 GVN System Repairing...")
    
    if os.path.exists(db_path):
        print(f"🗑️ Removing old database: {db_path}")
        try:
            # Close any connections and remove
            os.remove(db_path)
            print("✅ Old database removed successfully.")
        except Exception as e:
            print(f"❌ Error removing database: {e}")
            print("Trying manual migration instead...")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE user ADD COLUMN password_hash VARCHAR(128)")
                cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
                cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
                conn.commit()
                print("✅ Migration successful.")
            except Exception as e2:
                print(f"❌ Migration failed: {e2}")
            conn.close()

    print("🚀 Repair complete. Now start the app using 'python app.py'")
    print("This will automatically recreate the database with correct columns.")

if __name__ == "__main__":
    repair()
