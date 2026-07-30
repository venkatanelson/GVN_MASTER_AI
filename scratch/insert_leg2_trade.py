import sqlite3

db_path = "instance/gvn_algo_pro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Restore Row 2 (Morning 24150 CE trade 145.36 -> 178.63, PnL +4325.10)
cursor.execute("""
    UPDATE algo_trade
    SET entry_price = 145.36,
        target_price = 178.63,
        exit_price = 178.63,
        pnl = 4325.10,
        status = 'Target Hit'
    WHERE id = 2
""")

# Insert Row 4 for 2nd Leg (24150 CE 178.63 -> 211.91, PnL +4323.80)
cursor.execute("SELECT COUNT(*) FROM algo_trade WHERE id = 4 OR (symbol LIKE '%24150%' AND entry_price = 178.63);")
exists = cursor.fetchone()[0]

if not exists:
    cursor.execute("""
        INSERT INTO algo_trade (user_id, timestamp, symbol, quantity, trade_type, status, entry_price, pnl, exit_price, target_price, stop_loss)
        VALUES (1, '2026-07-30 14:40:00', 'NIFTY 24150 CE', 130, 'BUY', 'Target Hit', 178.63, 4323.80, 211.91, 211.91, 165.00)
    """)
    print("Inserted 2nd Leg 24150 CE trade (178.63 -> 211.91, PnL +4323.80)")
else:
    cursor.execute("""
        UPDATE algo_trade
        SET entry_price = 178.63,
            target_price = 211.91,
            exit_price = 211.91,
            pnl = 4323.80,
            status = 'Target Hit'
        WHERE id = 4 OR (symbol LIKE '%24150%' AND entry_price = 178.63)
    """)
    print("Updated 2nd Leg 24150 CE trade!")

conn.commit()

print("\n--- Current algo_trade rows in instance/gvn_algo_pro.db ---")
cursor.execute("SELECT id, user_id, timestamp, symbol, quantity, entry_price, target_price, exit_price, pnl, status FROM algo_trade;")
for row in cursor.fetchall():
    print(row)

conn.close()
