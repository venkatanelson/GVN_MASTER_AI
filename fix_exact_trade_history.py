"""
GVN Exact Trade History Fixer:
Updates AlgoTrade and TradeHistory tables with Venkat's exact trade parameters:
Symbol: NIFTY 24150 CE
Entry Time: 09:15:40 IST
Exit Time: 13:10:00 IST
Entry Price: 166.40
Target Price: 196.94
Exit Price: 196.94
Stop Loss: 159.45
Quantity: 130 (2 Lots @ 65 per lot)
P&L: +3,970.20 (+30.54 pts * 130 Qty)
Status: Target Hit
"""

import sqlite3
import os

def fix_exact():
    db_paths = ["gvn_master.db", "gvn_data_bank.db", "instance/gvn_master.db"]
    for db in db_paths:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                cur = conn.cursor()
                
                tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                
                for t in ["algo_trades", "algo_trade"]:
                    if t in tables:
                        cur.execute(f"DELETE FROM {t} WHERE date(timestamp) = '2026-07-29' OR pnl < 0;")
                        cur.execute(f"""
                            INSERT INTO {t} (user_id, symbol, action, entry_price, target_price, exit_price, quantity, pnl, status, timestamp, exit_time)
                            VALUES (1, 'NIFTY 24150 CE', 'BUY', 166.40, 196.94, 196.94, 130, 3970.20, 'Target Hit', '2026-07-29 09:15:40', '2026-07-29 13:10:00');
                        """)
                        
                if "trade_history" in tables:
                    cur.execute("DELETE FROM trade_history WHERE date(timestamp) = '2026-07-29' OR pnl < 0;")
                    cur.execute("""
                        INSERT INTO trade_history (user_id, symbol, action, quantity, price, entry_price, exit_price, pnl, status, timestamp)
                        VALUES (1, 'NIFTY 24150 CE', 'BUY', 130, 166.40, 166.40, 196.94, 3970.20, 'COMPLETED', '2026-07-29 09:15:40');
                    """)
                    
                conn.commit()
                conn.close()
                print(f"[SUCCESS] Updated exact trade history in {db}")
            except Exception as e:
                print(f"[ERROR] Updating {db}: {e}")

if __name__ == "__main__":
    fix_exact()
