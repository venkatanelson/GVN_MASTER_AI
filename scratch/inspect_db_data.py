import sqlite3
import json
import os

def main():
    db_path = "gvn_data_bank.db"
    if not os.path.exists(db_path):
        print(f"[-] Database {db_path} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print("Tables:", tables)
    
    if "option_915_benchmarks" in tables:
        print("\n--- option_915_benchmarks (last 20 records) ---")
        cursor.execute("SELECT * FROM option_915_benchmarks ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
    else:
        print("option_915_benchmarks table not found.")
        
    conn.close()

if __name__ == "__main__":
    main()
