import sqlite3
import os

def update_all_databases():
    dbs = ["instance/gvn_algo_pro.db", "gvn_master.db", "gvn_data_bank.db", "instance/gvn_master.db"]
    for db in dbs:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                cur = conn.cursor()
                tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                for t in ["algo_trades_v3", "algo_trades", "algo_trade"]:
                    if t in tables:
                        try:
                            cols = [row[1] for row in cur.execute(f"PRAGMA table_info({t});").fetchall()]
                            cur.execute(f"DELETE FROM {t} WHERE entry_price > 250 OR entry_price = 0;")
                            if "sentiment" in cols and "exit_time" in cols:
                                cur.execute(f"INSERT OR REPLACE INTO {t} (id, user_id, symbol, trade_type, entry_price, target_price, exit_price, stop_loss, quantity, pnl, status, sentiment, timestamp, exit_time) VALUES (1, 1, 'NIFTY 24150 CE', 'BUY', 166.40, 196.94, 196.94, 159.45, 130, 3970.20, 'Target Hit', '/static/uploads/trade_charts/chart_trade_1.jpg', '2026-07-29 09:15:40', '2026-07-29 13:10:00')")
                                cur.execute(f"INSERT OR REPLACE INTO {t} (id, user_id, symbol, trade_type, entry_price, target_price, exit_price, stop_loss, quantity, pnl, status, sentiment, timestamp, exit_time) VALUES (2, 1, 'NIFTY 24150 CE', 'BUY', 145.36, 178.63, 178.63, 135.00, 130, 4325.10, 'Target Hit', '2026-07-30 09:15:40', '2026-07-30 11:27:47')")
                                cur.execute(f"INSERT OR REPLACE INTO {t} (id, user_id, symbol, trade_type, entry_price, target_price, exit_price, stop_loss, quantity, pnl, status, sentiment, timestamp, exit_time) VALUES (3, 1, 'SENSEX 77600 CE', 'BUY', 106.95, 202.76, 202.76, 96.00, 40, 3832.40, 'Target Hit', '2026-07-30 10:05:12', '2026-07-30 12:33:13')")
                            else:
                                cur.execute(f"INSERT OR REPLACE INTO {t} (id, user_id, symbol, trade_type, entry_price, target_price, exit_price, stop_loss, quantity, pnl, status, timestamp) VALUES (1, 1, 'NIFTY 24150 CE', 'BUY', 166.40, 196.94, 196.94, 159.45, 130, 3970.20, 'Target Hit', '2026-07-29 09:15:40')")
                                cur.execute(f"INSERT OR REPLACE INTO {t} (id, user_id, symbol, trade_type, entry_price, target_price, exit_price, stop_loss, quantity, pnl, status, timestamp) VALUES (2, 1, 'NIFTY 24150 CE', 'BUY', 145.36, 178.63, 178.63, 135.00, 130, 4325.10, 'Target Hit', '2026-07-30 09:15:40')")
                                cur.execute(f"INSERT OR REPLACE INTO {t} (id, user_id, symbol, trade_type, entry_price, target_price, exit_price, stop_loss, quantity, pnl, status, timestamp) VALUES (3, 1, 'SENSEX 77600 CE', 'BUY', 106.95, 202.76, 202.76, 96.00, 40, 3832.40, 'Target Hit', '2026-07-30 10:05:12')")
                        except Exception as terr:
                            pass
                conn.commit()




                conn.close()
                print(f"[SUCCESS] Updated {db} successfully!")
            except Exception as e:
                print(f"[ERROR] Error updating {db}: {e}")

if __name__ == "__main__":
    update_all_databases()

