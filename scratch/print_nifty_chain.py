import json
import os
import sys

# Ensure stdout uses UTF-8 to avoid encoding errors on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

json_path = "live_market_data.json"

if not os.path.exists(json_path):
    print(f"File not found: {json_path}")
    exit(1)

with open(json_path, "r") as f:
    data = json.load(f)

nifty_scanner = data.get("scanner", {}).get("NIFTY", [])

print("=== NIFTY OPTION SCANNER DATA ===")
for item in nifty_scanner:
    strike = item.get("strike")
    ltp = item.get("ltp")
    oi_change = item.get("oi_change")
    volume = item.get("volume")
    pressure = item.get("pressure", "")
    ai_signal = item.get("ai_signal", "")
    levels = item.get("levels", {})
    
    print(f"Strike: {strike} | LTP: {ltp} | OI Change: {oi_change} | Vol: {volume}")
    print(f"  Pressure: {pressure} | AI Signal: {ai_signal}")
    if levels:
        levels_str = ", ".join([f"{k}: {v}" for k, v in levels.items()])
        print(f"  Levels  : {levels_str}")
    print("-" * 50)
