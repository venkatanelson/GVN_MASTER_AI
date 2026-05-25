import sqlite3
import os

db_path = "gvn_data_bank.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== NIFTY 9:15 BENCHMARKS FOR TODAY (2026-05-25) ===")
    cursor.execute("SELECT * FROM option_915_benchmarks WHERE timestamp LIKE '2026-05-25%' AND symbol = 'NIFTY' ORDER BY id ASC")
    rows = cursor.fetchall()
    print(f"Total NIFTY benchmarks today: {len(rows)}")
    for r in rows:
        row = dict(r)
        print(f"ID: {row.get('id')}, Strike: {row.get('strike')}, Type: {row.get('option_type')}, Delta: {row.get('delta')}, High: {row.get('high')}, Low: {row.get('low')}, i1: {row.get('i1')}, i5: {row.get('i5')}, i7: {row.get('i7')}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
