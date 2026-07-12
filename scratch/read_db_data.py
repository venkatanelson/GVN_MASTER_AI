import sqlite3
import os

db_path = os.path.abspath("instance/gvn_algo_pro.db")
print(f"Absolute DB Path: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")

for t in tables:
    print(f"\n--- Schema of {t} ---")
    cursor.execute(f"PRAGMA table_info({t});")
    cols = [col[1] for col in cursor.fetchall()]
    print(f"  Columns: {cols}")
    
    cursor.execute(f"SELECT COUNT(*) FROM {t};")
    count = cursor.fetchone()[0]
    print(f"  Total Rows: {count}")
    
    if count > 0:
        cursor.execute(f"SELECT * FROM {t} LIMIT 3;")
        print("  Sample Rows:")
        for r in cursor.fetchall():
            print(f"    {r}")

conn.close()
