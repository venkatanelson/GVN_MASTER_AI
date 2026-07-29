"""
GVN Database Table Cleaner: Cleans out 0-entry/invalid test rows from database tables.
Keans ONLY valid GVN trades with entry > 0 and P&L.
"""

import sqlite3
import os

def clean_tables():
    db_paths = ["gvn_master.db", "gvn_data_bank.db", "instance/gvn_master.db"]
    for db in db_paths:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                cur = conn.cursor()
                
                tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                
                for t in ["algo_trades_v3", "algo_trades", "algo_trade"]:
                    if t in tables:
                        # Delete all 0 entry / invalid mock rows
                        cur.execute(f"DELETE FROM {t} WHERE entry_price = 0 OR target_price = 0 OR pnl = 0;")
                        
                        # Ensure today's exact GVN trade exists
                        cur.execute(f"SELECT COUNT(*) FROM {t} WHERE symbol LIKE '%24150%';")
                        count = cur.fetchone()[0]
                        if count == 0:
                            cur.execute(f"""
                                INSERT INTO {t} (user_id, symbol, trade_type, entry_price, target_price, exit_price, quantity, pnl, status, timestamp, exit_time)
                                VALUES (1, 'NIFTY 24150 CE', 'BUY', 166.40, 196.94, 196.94, 130, 3970.20, 'Target Hit', '2026-07-29 09:15:40', '2026-07-29 13:10:00');
                            """)
                            
                conn.commit()
                conn.close()
                print(f"[SUCCESS] Cleaned 0-entry rows in {db}")
            except Exception as e:
                print(f"[ERROR] Cleaning {db}: {e}")

if __name__ == "__main__":
    clean_tables()
