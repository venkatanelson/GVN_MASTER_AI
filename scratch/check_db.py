
import sqlite3
import os

db_path = 'instance/gvn_algo_pro.db'
if not os.path.exists(db_path):
    print(f"❌ Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- User List ---")
    cursor.execute("SELECT id, username FROM user")
    print(cursor.fetchall())
    
    print("\n--- Broker Config List ---")
    cursor.execute("SELECT id, user_id, client_id FROM user_broker_config")
    print(cursor.fetchall())
    
    conn.close()
