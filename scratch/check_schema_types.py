import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_schema_types():
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(option_915_benchmarks)")
    columns = cursor.fetchall()
    print("Columns of option_915_benchmarks:")
    for col in columns:
        print(col)
        
    cursor.execute("SELECT * FROM option_915_benchmarks WHERE timestamp LIKE '2026-06-16%' AND symbol = 'NIFTY' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("\nSample NIFTY row:")
        for col, val in zip(columns, row):
            print(f"{col[1]} ({col[2]}): {val}")
    conn.close()

if __name__ == "__main__":
    check_schema_types()
