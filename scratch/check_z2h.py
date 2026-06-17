import sqlite3
import json

def check_dbs():
    print("=== gvn_data_bank.db ===")
    try:
        conn = sqlite3.connect("gvn_data_bank.db")
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables:", tables)
        
        # Fetch 9:15 option benchmarks
        cursor.execute("SELECT * FROM option_915_benchmarks ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        print("\nLatest 20 option benchmarks:")
        for r in rows:
            print(r)
            
        # Fetch latest wind history
        cursor.execute("SELECT * FROM market_wind_history ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        print("\nLatest 5 wind history rows:")
        for r in rows:
            print(r)
            
        conn.close()
    except Exception as e:
        print("Error checking gvn_data_bank.db:", e)
        
    print("\n=== instance/gvn_algo_pro.db ===")
    try:
        conn = sqlite3.connect("instance/gvn_algo_pro.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables:", tables)
        conn.close()
    except Exception as e:
        print("Error checking gvn_algo_pro.db:", e)

if __name__ == "__main__":
    check_dbs()
