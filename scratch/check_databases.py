import sqlite3
import os

databases = [
    'instance/gvn_algo_pro.db',
    'instance/gvn_master_algo.db',
    'gvn_data_bank.db',
    'gvn_master.db'
]

for db_path in databases:
    if not os.path.exists(db_path):
        print(f"File not found: {db_path}")
        continue
    print("=" * 60)
    print(f"DATABASE: {db_path}")
    print("=" * 60)
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cur.fetchall()]
        print(f"Tables: {tables}")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  Table: {table} | Row count: {count}")
            if count > 0:
                # print schema of columns
                cur.execute(f"PRAGMA table_info({table})")
                cols = [c[1] for c in cur.fetchall()]
                print(f"    Columns: {cols}")
                # print last 3 rows
                try:
                    cur.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 3")
                    rows = cur.fetchall()
                    print(f"    Last 3 rows:")
                    for r in rows:
                        print(f"      {r}")
                except Exception as row_err:
                    # Table might not have standard rowid or ordering
                    cur.execute(f"SELECT * FROM {table} LIMIT 3")
                    rows = cur.fetchall()
                    print(f"      {rows}")
        conn.close()
    except Exception as e:
        print(f"Error querying {db_path}: {e}")
    print("\n")
