import sqlite3

db_path = 'instance/gvn_algo_pro.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
print('Current columns in user table:')
for col in columns:
    print(f'  {col[1]} ({col[2]})')

conn.close()
