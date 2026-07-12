import sqlite3
from datetime import datetime

db_path = "instance/gvn_algo_pro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get columns for trade_history
cursor.execute("PRAGMA table_info(trade_history);")
cols = [col[1] for col in cursor.fetchall()]
print(f"Columns: {cols}")

# Select all trade_history from today
today_str = "2026-07-09"
cursor.execute("SELECT * FROM trade_history ORDER BY timestamp ASC;")
rows = cursor.fetchall()

today_trades = []
for r in rows:
    # Check if timestamp contains today_str
    # Column index 2 is timestamp
    ts = r[2]
    if isinstance(ts, str) and ts.startswith(today_str):
        today_trades.append(r)

print(f"\nFound {len(today_trades)} trade entries for today ({today_str})")

# We want to group by unique symbol & timestamp or user to show unique signal activations
# Since multiple users might execute the same signal, we can group by (symbol, entry_price, exit_price, reason)
unique_signals = {}
for r in today_trades:
    # Create dict representation
    trade_dict = dict(zip(cols, r))
    # Unique key for signal
    key = (trade_dict.get("symbol"), trade_dict.get("price"), trade_dict.get("reason"))
    if key not in unique_signals:
        unique_signals[key] = {
            "symbol": trade_dict.get("symbol"),
            "action": trade_dict.get("action"),
            "timestamp": trade_dict.get("timestamp"),
            "entry_price": trade_dict.get("price"), # check if price or entry_price holds the actual entry value
            "exit_price": trade_dict.get("exit_price"),
            "status": trade_dict.get("status"),
            "reason": trade_dict.get("reason"),
            "pnl": trade_dict.get("pnl"),
            "raw_pnl": trade_dict.get("pnl"), # check if it's the actual pnl
            "qty": trade_dict.get("quantity")
        }

print("\n--- Unique Signal Activations Today ---")
for idx, sig in enumerate(unique_signals.values(), 1):
    print(f"{idx}. {sig['timestamp']} | {sig['symbol']} | {sig['action']} | Status: {sig['status']} | Entry: {sig['entry_price']} | Exit: {sig['exit_price']} | Reason: {sig['reason']}")

conn.close()
