import sqlite3
import pandas as pd
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=== ANALYZING TODAY'S MARKET DATA AT 24950 ===")

# Check gvn_data_bank.db option_chain_history for today
conn = sqlite3.connect('gvn_data_bank.db')
df = pd.read_sql_query("SELECT * FROM option_chain_history WHERE timestamp LIKE '2026-07-27%' ORDER BY timestamp ASC", conn)

print(f"Total option chain records today (2026-07-27): {len(df)}")
if not df.empty:
    print("Columns:", df.columns.tolist())
    print("Unique symbols:", df['symbol'].unique())
    print("Time range:", df['timestamp'].min(), "to", df['timestamp'].max())
    
    # Check strikes around 24950 or spot prices
    print("\nSample records for NIFTY:")
    nifty_df = df[df['symbol'] == 'NIFTY']
    print(nifty_df[['timestamp', 'strike', 'option_type', 'ltp', 'volume', 'oi', 'oi_change']].head(10))

# Check live_market_data.json
if os.path.exists('live_market_data.json'):
    with open('live_market_data.json', 'r', encoding='utf-8') as f:
        lmd = json.load(f)
        print("\n--- LIVE MARKET DATA SUMMARY ---")
        print(json.dumps(lmd.get('summary', {}), indent=2))
        print("\n--- SCANNER HIGHLIGHTS ---")
        scanner = lmd.get('scanner', {})
        for k, v in scanner.items():
            print(f"Key: {k}, Value snippet: {str(v)[:200]}")

# Check live_market_history.csv if available
if os.path.exists('live_market_history.csv'):
    print("\n--- CHECKING live_market_history.csv FOR 24950 ---")
    try:
        # Read last 1000 lines of CSV
        import subprocess
        result = subprocess.run(['powershell', '-Command', 'Get-Content live_market_history.csv -Tail 100'], capture_output=True, text=True)
        print("Last 10 lines of live_market_history.csv:")
        print('\n'.join(result.stdout.splitlines()[-10:]))
    except Exception as e:
        print("CSV tail error:", e)
