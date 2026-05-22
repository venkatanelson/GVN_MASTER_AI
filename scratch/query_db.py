import sqlite3
import os

def inspect_ce():
    db_path = "gvn_data_bank.db"
    if not os.path.exists(db_path):
        print(f"{db_path} does not exist")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query option_915_benchmarks for strike 23550
    cursor.execute("SELECT * FROM option_915_benchmarks WHERE strike = 23550")
    rows = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]
    print(f"\n=== Entries in option_915_benchmarks for Strike 23550 ===")
    for r in rows:
        print(dict(zip(col_names, r)))
        
    conn.close()

if __name__ == "__main__":
    inspect_ce()
