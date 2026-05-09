
import sqlite3
import os

db_path = 'instance/gvn_algo_pro.db'
report_path = 'db_report.txt'

with open(report_path, 'w', encoding='utf-8') as f:
    if not os.path.exists(db_path):
        f.write(f"Database not found at {db_path}")
    else:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        f.write("--- User List ---\n")
        cursor.execute("SELECT id, username FROM user")
        f.write(str(cursor.fetchall()) + "\n")
        
        f.write("\n--- Broker Config List ---\n")
        cursor.execute("SELECT id, user_id, client_id FROM user_broker_config")
        f.write(str(cursor.fetchall()) + "\n")
        
        conn.close()
        f.write("\nReport Generated Successfully.")
