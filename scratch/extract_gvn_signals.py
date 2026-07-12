import sqlite3
from datetime import datetime, timedelta

db_path = "instance/gvn_algo_pro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get columns of algo_trades_v3
cursor.execute("PRAGMA table_info(algo_trades_v3);")
cols = [col[1] for col in cursor.fetchall()]

# Select trades from today (UTC timestamp starts with 2026-07-09)
cursor.execute("SELECT * FROM algo_trades_v3 WHERE timestamp LIKE '2026-07-09%' ORDER BY timestamp ASC;")
rows = cursor.fetchall()

print(f"Found {len(rows)} raw user executions today in algo_trades_v3.")

# Group by unique trade signal parameters
unique_trades = {}
for r in rows:
    trade_dict = dict(zip(cols, r))
    symbol = trade_dict.get("symbol")
    entry_p = trade_dict.get("entry_price")
    exit_p = trade_dict.get("exit_price")
    trade_type = trade_dict.get("trade_type")
    sentiment_reason = trade_dict.get("sentiment")
    
    # Group key
    key = (symbol, trade_type, entry_p, exit_p, sentiment_reason)
    if key not in unique_trades:
        # Convert UTC timestamp string to datetime then to IST (+5.5 hours)
        utc_time_str = trade_dict.get("timestamp")
        try:
            utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S")
            
        ist_dt = utc_dt + timedelta(hours=5, minutes=30)
        
        # Calculate percentage change
        pct_change = 0.0
        if entry_p and entry_p > 0:
            pct_change = ((exit_p - entry_p) / entry_p) * 100
            
        # Format PnL per lot
        pnl = trade_dict.get("pnl", 0.0)
        
        unique_trades[key] = {
            "symbol": symbol,
            "trade_type": trade_type,
            "ist_time": ist_dt.strftime("%I:%M:%S %p"),
            "entry_price": entry_p,
            "exit_price": exit_p,
            "pnl_per_lot": pnl,
            "pct": round(pct_change, 1),
            "reason": sentiment_reason,
            "status": trade_dict.get("status")
        }

print("\n--- Formatted Unique Trades ---")
for idx, sig in enumerate(unique_trades.values(), 1):
    print(f"Trade {idx}:")
    print(f"  Time (IST) : {sig['ist_time']}")
    print(f"  Symbol     : {sig['symbol']}")
    print(f"  Type       : {sig['trade_type']}")
    print(f"  Entry Price: Rs. {sig['entry_price']:.2f}")
    print(f"  Exit Price : Rs. {sig['exit_price']:.2f} ({sig['pct']}% Change)")
    print(f"  P&L/Lot    : Rs. {sig['pnl_per_lot']:.2f}")
    print(f"  Reason     : {sig['reason']}")
    print(f"  Status     : {sig['status']}")
    print("-" * 40)

conn.close()
