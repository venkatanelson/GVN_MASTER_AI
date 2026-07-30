import sqlite3
import os

db_path = "gvn_data_bank.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in gvn_data_bank.db:", tables)
    for table in tables:
        tname = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {tname};")
        count = cursor.fetchone()[0]
        print(f"Table {tname}: {count} rows")
    conn.close()
else:
    print("gvn_data_bank.db does not exist")
