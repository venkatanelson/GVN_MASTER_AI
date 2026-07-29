import sqlite3
import json
import os
import pandas as pd

print("=== CHECKING DATABASES ===")
for dbname in ['gvn_data_bank.db', 'gvn_master.db']:
    if os.path.exists(dbname):
        print(f"\n--- {dbname} ---")
        conn = sqlite3.connect(dbname)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", tables)
        for t in tables:
            tname = t[0]
            try:
                df = pd.read_sql_query(f"SELECT * FROM {tname} ORDER BY rowid DESC LIMIT 10", conn)
                print(f"Table {tname} count: {pd.read_sql_query(f'SELECT count(*) FROM {tname}', conn).values[0][0]}")
                print(df.head(3))
            except Exception as e:
                print(f"Error reading {tname}: {e}")

print("\n=== CHECKING LIVE MARKET DATA JSON ===")
if os.path.exists('live_market_data.json'):
    with open('live_market_data.json', 'r') as f:
        data = json.load(f)
        if isinstance(data, dict):
            print("Keys:", list(data.keys()))
            for k in list(data.keys())[:5]:
                print(k, "->", str(data[k])[:150])
        elif isinstance(data, list):
            print("Length:", len(data))
            print("Sample 0:", str(data[0])[:200])

print("\n=== CHECKING MORNING LOCKED STRIKES ===")
if os.path.exists('morning_locked_strikes.json'):
    with open('morning_locked_strikes.json', 'r') as f:
        print(f.read())
