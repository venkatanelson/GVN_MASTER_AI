import requests
import json
import pyotp
import os
import sqlite3
from datetime import datetime

def get_totp(totp_key):
    return pyotp.TOTP(totp_key).now()

def main():
    # 1. Credentials
    client_id = "P218754"
    password = "3061"
    totp_key = "U7IPZ7XFZELCONOX6SHPM4C7I4"
    api_key = "JGYxHp6d"

    totp = get_totp(totp_key)
    
    headers = {
        "Content-Type": "application/json", "Accept": "application/json",
        "X-UserType": "USER", "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00", "X-PrivateKey": api_key,
        "User-Agent": "Mozilla/5.0"
    }
    payload = {"clientcode": client_id, "password": password, "totp": totp}
    
    print("Logging in to Angel One...")
    resp = requests.post("https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword", json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"Login failed HTTP {resp.status_code}: {resp.text}")
        return
        
    rj = resp.json()
    if not rj.get('status'):
        print(f"Login response error: {rj}")
        return
        
    jwt = rj.get('data', {}).get('jwtToken')
    print("Login successful! JWT obtained.")
    headers["Authorization"] = f"Bearer {jwt}"

    # 2. Get OHLC for 23600 CE (Token: 72143) and 23750 PE (Token: 72170)
    strikes = {
        "23600 CE": {"token": "72143", "type": "CE", "strike_val": 23600.0},
        "23750 PE": {"token": "72170", "type": "PE", "strike_val": 23750.0}
    }
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Let's check JSON file first
    json_path = "gvn_recorded_915_ohlc.json"
    json_data = {}
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            try:
                json_data = json.load(f)
            except:
                pass
    
    json_data["date"] = today_str
    if "NIFTY" not in json_data:
        json_data["NIFTY"] = {}

    for strike_key, info in strikes.items():
        hist_payload = {
            "exchange": "NFO",
            "symboltoken": info["token"],
            "interval": "ONE_MINUTE",
            "fromdate": f"{today_str} 09:15",
            "todate": f"{today_str} 09:20"
        }
        
        print(f"Fetching candle data for {strike_key}...")
        hist_resp = requests.post("https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/v1/getCandleData", json=hist_payload, headers=headers)
        if hist_resp.status_code != 200:
            print(f"Failed for {strike_key}: {hist_resp.text}")
            continue
            
        hrj = hist_resp.json()
        if not hrj.get("status"):
            print(f"Error for {strike_key}: {hrj}")
            continue
            
        candles = hrj.get("data")
        if not candles:
            print(f"No candles returned for {strike_key}")
            continue
            
        # Parse 9:15 candle (first one matching 09:15)
        c_915 = None
        for c in candles:
            if "09:15" in c[0]:
                c_915 = c
                break
        if not c_915:
            c_915 = candles[0]
            
        high = float(c_915[2])
        low = float(c_915[3])
        print(f"Real OHLC for {strike_key}: High={high}, Low={low}")
        
        # Save to JSON
        json_data["NIFTY"][strike_key] = {
            "high": high,
            "low": low,
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate levels
        diff = high - low
        result = diff / 2
        n1 = high + result
        n2 = low + result
        
        gvn0 = n2 * 0.118 / 0.5
        gvn100 = n1 * 0.786 / 0.5
        gvnR = gvn100 - gvn0
        
        i1 = round(gvn100, 2)
        i5 = round(gvn0 + 0.5 * gvnR, 2)
        i7 = round(gvn0 + 0.220 * gvnR, 2)
        
        # Update SQLite Databases
        db_paths = ["gvn_master.db", "gvn_data_bank.db"]
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Delete any placeholder entry for today
                    cursor.execute("""
                        DELETE FROM option_915_benchmarks
                        WHERE strike = ? AND option_type = ? AND date(timestamp) = ?
                    """, (info["strike_val"], info["type"], today_str))
                    
                    # Insert fresh real levels
                    cursor.execute("""
                        INSERT INTO option_915_benchmarks (timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7)
                        VALUES (?, 'NIFTY', ?, ?, ?, ?, 0.60, ?, ?, ?)
                    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), info["strike_val"], info["type"], high, low, i1, i5, i7))
                    conn.commit()
                    conn.close()
                    print(f"Updated benchmarks in {db_path} for {strike_key}")
                except Exception as e:
                    print(f"Error updating DB {db_path}: {e}")

    # Write updated JSON
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=4)
    print("JSON file updated successfully.")

if __name__ == "__main__":
    main()
