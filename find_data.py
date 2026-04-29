import sqlite3
conn = sqlite3.connect('gvn_algo_pro.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in DB: {tables}")
for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"Table: {table[0]} | Rows: {count}")
    except: pass
conn.close()
