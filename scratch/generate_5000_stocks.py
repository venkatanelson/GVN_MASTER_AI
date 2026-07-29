import json
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

master_path = r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\angel_scrip_master.json"
output_path = r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\indian_all_stocks_5000.csv"

if not os.path.exists(master_path):
    print("Error: angel_scrip_master.json not found!")
    sys.exit(1)

print("Loading scrip master...")
with open(master_path, "r", encoding="utf-8") as f:
    master_data = json.load(f)

print(f"Loaded {len(master_data)} items from scrip master.")

stocks = []
seen = set()

# Allowed NSE Series/Groups for actual equities
allowed_nse_series = {'EQ', 'BE', 'SM', 'ST', 'BZ'}

for item in master_data:
    exch = item.get('exch_seg')
    inst_type = item.get('instrumenttype')
    expiry = item.get('expiry')
    symbol = item.get('symbol')
    token = item.get('token')
    name = item.get('name')
    
    if expiry == "" and inst_type == "":
        is_valid = False
        series = ""
        clean_symbol = symbol
        
        # 1. Filter NSE equities
        if exch == 'NSE':
            series = symbol.split('-')[-1] if '-' in symbol else 'EQ'
            clean_symbol = symbol.split('-')[0] if '-' in symbol else symbol
            if series in allowed_nse_series:
                is_valid = True
                
        # 2. Filter BSE equities (6-digit token starting with 5)
        elif exch == 'BSE':
            if len(token) == 6 and token.startswith('5'):
                is_valid = True
                series = 'BSE_EQ'
                
        if is_valid:
            key = (clean_symbol, exch)
            if key not in seen:
                seen.add(key)
                stocks.append({
                    'Exchange': exch,
                    'Symbol': clean_symbol,
                    'Company Name': name,
                    'Token': token,
                    'Series/Group': series
                })

print(f"Filtered {len(stocks)} pure equity stocks.")

# Sort stocks by Exchange and Symbol
stocks.sort(key=lambda x: (x['Exchange'], x['Symbol']))

# Write to CSV
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=['Exchange', 'Symbol', 'Company Name', 'Token', 'Series/Group'])
    writer.writeheader()
    writer.writerows(stocks)

print(f"Successfully generated CSV at: {output_path}")
