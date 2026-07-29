import sqlite3
import pandas as pd
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

print("=== DETAILED TODAY 2026-07-27 OPTION CHAIN ===")
conn = sqlite3.connect('gvn_data_bank.db')
df = pd.read_sql_query("SELECT * FROM option_chain_history ORDER BY id DESC LIMIT 50", conn)
print(df[['timestamp', 'symbol', 'strike_price', 'option_type', 'ltp', 'delta', 'oi', 'oi_change', 'volume']])

print("\n=== SEARCHING LOGS FOR 24950 / REVERSAL / BREAK ===")
if os.path.exists('gvn_dashboard.log'):
    with open('gvn_dashboard.log', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        relevant = [l for l in lines if '24950' in l or '24900' in l or '25000' in l or 'reversal' in l.lower() or 'break' in l.lower()]
        print(f"Found {len(relevant)} matching log lines. Last 20:")
        for r in relevant[-20:]:
            print(r.strip())
