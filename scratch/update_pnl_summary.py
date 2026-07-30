import sqlite3

db_path = "instance/gvn_algo_pro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- daily_pnl_tracker table ---")
cursor.execute("SELECT * FROM daily_pnl_tracker;")
rows = cursor.fetchall()
for r in rows:
    print(r)

# Update today's PnL in daily_pnl_tracker if present
cursor.execute("""
    UPDATE daily_pnl_tracker
    SET total_pnl = 9694.10
    WHERE date LIKE '%30 Jul%' OR date LIKE '%2026-07-30%'
""")
conn.commit()
print("Updated daily_pnl_tracker!")

conn.close()
