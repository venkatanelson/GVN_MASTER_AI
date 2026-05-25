import sqlite3
import os

db_path = "gvn_data_bank.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== DISTINCT OPTION TYPES IN option_915_benchmarks ===")
    cursor.execute("SELECT option_type, COUNT(*) FROM option_915_benchmarks GROUP BY option_type")
    print(cursor.fetchall())
    
    print("\n=== DISTINCT DATES IN option_915_benchmarks ===")
    cursor.execute("SELECT date(timestamp), COUNT(*) FROM option_915_benchmarks GROUP BY date(timestamp)")
    print(cursor.fetchall())
    
    print("\n=== SAMPLE PE ROWS IN option_915_benchmarks ===")
    cursor.execute("SELECT * FROM option_915_benchmarks WHERE option_type = 'PE' LIMIT 5")
    print(cursor.fetchall())
    
    conn.close()
else:
    print(f"Database not found at {db_path}")
