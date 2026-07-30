import sqlite3

db_path = "instance/gvn_algo_pro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- user table ---")
cursor.execute("SELECT id, username, email FROM user;")
for u in cursor.fetchall():
    print(u)

print("\n--- algo_trade table ---")
cursor.execute("SELECT * FROM algo_trade;")
trades = cursor.fetchall()
for tr in trades:
    print(tr)

# Get column names of algo_trade
cursor.execute("PRAGMA table_info(algo_trade);")
cols = [c[1] for c in cursor.fetchall()]
print("\nalgo_trade columns:", cols)

# Update the 30 Jul NIFTY 24150 CE trade in algo_trade table
cursor.execute("""
    UPDATE algo_trade
    SET target_price = 252.80,
        exit_price = 190.50,
        pnl = 5861.70,
        status = '0.2.2.2 TGT ACTIVE'
    WHERE symbol LIKE '%24150%'
""")
conn.commit()
print(f"\nUpdated {cursor.rowcount} rows in algo_trade table!")

print("\n--- Updated algo_trade table ---")
cursor.execute("SELECT * FROM algo_trade;")
for tr in cursor.fetchall():
    print(tr)

conn.close()
