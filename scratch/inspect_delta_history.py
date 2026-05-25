import sqlite3
import os

db_path = "gvn_data_bank.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM option_chain_history")
    print("Total rows in option_chain_history:", cursor.fetchone()[0])
    
    cursor.execute("SELECT COUNT(*) FROM option_chain_history WHERE timestamp LIKE '2026-05-25%'")
    print("Total rows today:", cursor.fetchone()[0])
    
    cursor.execute("SELECT DISTINCT symbol FROM option_chain_history WHERE timestamp LIKE '2026-05-25%'")
    print("Distinct symbols today:", cursor.fetchall())
    
    conn.close()
else:
    print(f"Database not found at {db_path}")
