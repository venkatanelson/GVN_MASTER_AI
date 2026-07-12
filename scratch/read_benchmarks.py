import sqlite3
import os

print("--- DB: instance/gvn_algo_pro.db ---")
if os.path.exists("instance/gvn_algo_pro.db"):
    conn = sqlite3.connect("instance/gvn_algo_pro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    # Let's query option_915_benchmarks table
    if "option_915_benchmarks" in tables:
        cursor.execute("SELECT * FROM option_915_benchmarks WHERE timestamp LIKE '2026-07-09%' OR strike LIKE '%23900%' OR strike LIKE '%2395%';")
        print("Rows:")
        for r in cursor.fetchall():
            print(r)
    conn.close()

print("\n--- DB: gvn_data_bank.db ---")
if os.path.exists("gvn_data_bank.db"):
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    if "option_915_benchmarks" in tables:
        cursor.execute("SELECT * FROM option_915_benchmarks WHERE strike LIKE '%23900%' OR strike LIKE '%2395%';")
        print("Rows:")
        for r in cursor.fetchall():
            print(r)
    conn.close()
