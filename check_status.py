import sqlite3
import os

db_path = 'instance/gvn_algo_pro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Last 5 Algo Trades ---")
    cursor.execute("SELECT * FROM algo_trades_v3 ORDER BY timestamp DESC LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- Last 5 AI Paper Trades ---")
    cursor.execute("SELECT * FROM ai_paper_trades ORDER BY timestamp DESC LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- User Algo Status ---")
    cursor.execute("SELECT username, algo_status, is_approved, expiry_date FROM user")
    for row in cursor.fetchall():
        print(row)
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
