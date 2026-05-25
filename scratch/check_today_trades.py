import sqlite3
import os

db_path = 'instance/gvn_algo_pro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== TODAY'S ALGO TRADES FOR USER 1 (2026-05-25) ===")
    cursor.execute("SELECT * FROM algo_trades_v3 WHERE timestamp LIKE '2026-05-25%' AND user_id = 1 ORDER BY timestamp ASC")
    trades = cursor.fetchall()
    print(f"Total trades today for user 1: {len(trades)}")
    for row in trades:
        row_dict = dict(row)
        print(f"ID: {row_dict.get('id')}, Time: {row_dict.get('timestamp')}, Symbol: {row_dict.get('symbol')}, Type: {row_dict.get('trade_type')}, Status: {row_dict.get('status')}, Entry: {row_dict.get('entry_price')}, Exit: {row_dict.get('exit_price')}, PnL: {row_dict.get('pnl')}, Signal: {row_dict.get('sentiment') or row_dict.get('signal_name')}")
        
    print("\n=== ALL TRADES FOR USER 1 TODAY (ANY STATUS) ===")
    # let's make sure we didn't miss anything that has a different timestamp format or is open
    cursor.execute("SELECT * FROM algo_trades_v3 WHERE user_id = 1 ORDER BY id DESC LIMIT 20")
    recent = cursor.fetchall()
    for row in recent:
        row_dict = dict(row)
        print(f"ID: {row_dict.get('id')}, Time: {row_dict.get('timestamp')}, Symbol: {row_dict.get('symbol')}, Type: {row_dict.get('trade_type')}, Status: {row_dict.get('status')}, Entry: {row_dict.get('entry_price')}, Exit: {row_dict.get('exit_price')}, PnL: {row_dict.get('pnl')}, Signal: {row_dict.get('sentiment') or row_dict.get('signal_name')}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
