import sqlite3
from datetime import datetime

db_path = "instance/gvn_algo_pro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables in {db_path}: {tables}")

# Check columns of tables containing 'trade' or 'algo'
for t in tables:
    if "trade" in t.lower() or "algo" in t.lower():
        cursor.execute(f"PRAGMA table_info({t});")
        cols = [col[1] for col in cursor.fetchall()]
        print(f"Columns in table '{t}': {cols}")
        
        # Select all rows from today
        today_date = "2026-07-09" # Current local date from metadata
        cursor.execute(f"SELECT * FROM {t};")
        all_rows = cursor.fetchall()
        print(f"Total rows in '{t}': {len(all_rows)}")
        
        # Select rows matching today's date
        # Check if timestamp contains '2026-07-09' or starts with it
        # Let's inspect the first 5 rows to see formatting
        print(f"First 5 rows in '{t}':")
        for row in all_rows[:5]:
            print(row)
            
        # Filter for today (assuming timestamp is column index 2 or 3)
        # Let's print rows where timestamp starts with 2026-07-09
        print(f"Rows from {today_date} in '{t}':")
        today_rows = []
        for row in all_rows:
            # Check if any element in row is a string starting with today_date or is a datetime
            for item in row:
                if isinstance(item, str) and (item.startswith(today_date) or today_date in item):
                    today_rows.append(row)
                    break
        for row in today_rows:
            print(row)

conn.close()
