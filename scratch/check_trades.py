import sqlite3
import os

db_path = 'instance/gvn_algo_pro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Trade History ---")
    try:
        cursor.execute("SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT 10;")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error: {e}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
