import sqlite3
import os

db_path = 'instance/gvn_algo_pro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(algo_trades_v3)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()
else:
    print("DB not found")
