import os
import sqlite3

def clean_and_compress():
    print("🛠️ GVN AUTO-RECOVERY: DISK FULL FIXED 🛠️")
    print("=========================================")
    
    # 1. Vacuum SQLite database to release all unused space
    db_file = "gvn_data_bank.db"
    if os.path.exists(db_file):
        print(f"📦 Compressing Database ({os.path.getsize(db_file)/1024:.2f} KB)...")
        try:
            conn = sqlite3.connect(db_file)
            conn.execute("VACUUM;")
            conn.commit()
            conn.close()
            print("✅ Database compression and VACUUM successful!")
        except Exception as e:
            print(f"❌ Database VACUUM failed: {e}")
            
    # 2. Delete temporary .db-wal and .db-journal files if database is closed
    for ext in ['-wal', '-journal', '-shm']:
        temp_f = db_file + ext
        if os.path.exists(temp_f):
            try:
                os.remove(temp_f)
                print(f"✅ Cleaned up temporary lock file: {temp_f}")
            except Exception as e:
                print(f"⚠️ Could not delete {temp_f}: {e}")

    # 3. Clean huge log files
    log_files = ['nse_status.log', 'shoonya_feed_status.log', 'dhan_feed_status.log']
    for log in log_files:
        if os.path.exists(log):
            try:
                size = os.path.getsize(log)
                os.remove(log)
                print(f"✅ Deleted huge log file: {log} ({size/1024:.2f} KB freed)")
            except Exception as e:
                print(f"❌ Failed to delete {log}: {e}")

    print("\n🚀 Recovery finished! Please pause OneDrive sync and run: python app.py")

if __name__ == "__main__":
    clean_and_compress()
