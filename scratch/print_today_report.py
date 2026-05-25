import json
import sqlite3
import os

print("=== GVN ALGO REPORT FOR TODAY (2026-05-25) ===")

# 1. Load morning locked strikes
strikes_path = "morning_locked_strikes.json"
if os.path.exists(strikes_path):
    with open(strikes_path, "r") as f:
        strikes = json.load(f)
    print("\n[Morning Locked Strikes]")
    for index, val in strikes.items():
        if index != "date":
            print(f" - {index}: Spot = {val.get('spot')}, CE Strike = {val.get('CE')}, PE Strike = {val.get('PE')}")
else:
    print("\n[Morning Locked Strikes] File not found.")

# 2. Load 9:15 OHLC values
ohlc_path = "gvn_recorded_915_ohlc.json"
if os.path.exists(ohlc_path):
    with open(ohlc_path, "r") as f:
        ohlc = json.load(f)
    print("\n[9:15 AM Spot Candle High/Low]")
    # Look for spot keys
    for index in ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]:
        idx_data = ohlc.get(index, {})
        spot_key = f"{index}_SPOT"
        if spot_key in idx_data:
            spot_ohlc = idx_data[spot_key]
            print(f" - {index} Spot: High = {spot_ohlc.get('high')}, Low = {spot_ohlc.get('low')}")
        else:
            # Maybe it is directly under index or formatted differently
            # Let's search index data keys for "SPOT"
            spot_found = False
            for k, v in idx_data.items():
                if "SPOT" in k:
                    print(f" - {index} Spot ({k}): High = {v.get('high')}, Low = {v.get('low')}")
                    spot_found = True
                    break
            if not spot_found:
                print(f" - {index} Spot: Not found in recorded OHLC JSON.")
else:
    print("\n[9:15 AM OHLC] File not found.")

# 3. Fetch Trades for all active users today
db_path = "instance/gvn_algo_pro.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT username, algo_status FROM user WHERE algo_status = 'ON'")
    active_users = [row['username'] for row in cursor.fetchall()]
    print(f"\n[Active Users today]: {', '.join(active_users)}")
    
    cursor.execute("SELECT * FROM algo_trades_v3 WHERE timestamp LIKE '2026-05-25%' ORDER BY timestamp ASC")
    trades = cursor.fetchall()
    print(f"\n[All Trades Executed Today ({len(trades)} total across all users)]")
    # Group trades by Symbol, Type, Signal, Entry, Exit, Pnl to make it readable
    grouped_trades = {}
    for r in trades:
        row = dict(r)
        key = (row['symbol'], row['trade_type'], row['entry_price'], row['exit_price'], row['status'], row['pnl'], row['sentiment'])
        if key not in grouped_trades:
            grouped_trades[key] = []
        grouped_trades[key].append(row['user_id'])
    
    for key, user_ids in grouped_trades.items():
        symbol, trade_type, entry, exit, status, pnl, signal = key
        print(f" - Symbol: {symbol} | Type: {trade_type} | Entry: {entry} | Exit: {exit} | PnL: {pnl} | Status: {status} | Signal: {signal} | Executed for {len(user_ids)} users (IDs: {user_ids})")
        
    conn.close()
else:
    print(f"\n[Database] {db_path} not found.")
