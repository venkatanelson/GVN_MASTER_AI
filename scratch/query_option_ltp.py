import os
import sys
import json
import requests
import pyotp
from datetime import datetime

# Reconfigure stdout for UTF-8 to prevent encoding crashes on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shared_data
from broker_api import angel_http_login

def calculate_gvn_levels(high915, low915):
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    levels = {
        "i1": round(gvn100, 2),
        "i3": round(gvn0 + 0.618 * gvnR, 2),
        "i5": round(gvn0 + 0.500 * gvnR, 2),
        "i6": round(gvn0 + 0.382 * gvnR, 2),
        "i7": round(gvn0 + 0.220 * gvnR, 2),
        "i0": round(gvn0, 2)
    }
    return levels

def main():
    print("=== GVN LEVELS CALCULATION ===")
    high = 271.15
    low = 210.00
    levels = calculate_gvn_levels(high, low)
    print(f"High: {high}, Low: {low}")
    for k, v in levels.items():
        print(f"  {k}: {v}")
    
    scrip_path = "../angel_scrip_master.json"
    if not os.path.exists(scrip_path):
        scrip_path = "angel_scrip_master.json"
        
    print("Loading Angel Scrip Master...")
    with open(scrip_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)
        
    print("Searching for NIFTY 23550 CE options...")
    matched_options = []
    for item in master_data:
        if item.get('exch_seg') == 'NFO' and item.get('name') == 'NIFTY':
            try:
                strike_val = float(item.get('strike', 0))
                if abs(strike_val - 23550.0) < 1.0 or abs(strike_val/100.0 - 23550.0) < 1.0:
                    symbol = item.get('symbol', '')
                    if symbol.endswith('CE'):
                        matched_options.append(item)
            except:
                pass
                
    print(f"Found {len(matched_options)} matching options:")
    for opt in matched_options:
        print(f"  Symbol: {opt.get('symbol')} | Token: {opt.get('token')} | Expiry: {opt.get('expiry')} | Strike: {opt.get('strike')}")
        
    if not matched_options:
        print("No options matched NIFTY 23550 CE")
        return

    # Login to Angel
    print("\nLogging into Angel One...")
    cfg = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel")
    jwt_token = angel_http_login(cfg)
    if not jwt_token:
        print("Failed to login to Angel One.")
        return
    print("Logged in successfully.")
    
    # Query LTP for each matched option
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": cfg.get("api_key"),
        "Authorization": f"Bearer {jwt_token}",
        "User-Agent": "Mozilla/5.0"
    }
    
    url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/market/v1/quote/"
    
    tokens = [opt.get('token') for opt in matched_options]
    payload = {
        "mode": "LTP",
        "exchangeTokens": {
            "NFO": tokens
        }
    }
    
    print("Fetching quote...")
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        print("Raw Response Data:")
        print(json.dumps(data, indent=2))
        
        if data.get('status') and data.get('data'):
            fetched = data['data'].get('fetched', [])
            print("\nLive Quote Data:")
            for item in fetched:
                # Let's inspect the keys
                print("Item keys:", item.keys())
                token = item.get('token') or item.get('symbolToken') or item.get('symboltoken')
                ltp = item.get('ltp', 0.0)
                opt_info = next((o for o in matched_options if str(o.get('token')) == str(token)), {})
                symbol_name = opt_info.get('symbol', 'Unknown')
                expiry = opt_info.get('expiry', 'Unknown')
                print(f"  Matched Symbol: {symbol_name} | Token: {token} | Expiry: {expiry} | LTP: Rs. {ltp}")
    else:
        print(f"HTTP Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    main()
