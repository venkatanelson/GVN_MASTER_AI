import sys
import os
import requests
import json
from datetime import datetime

def show_usage():
    print("GVN Master Algo - Admin Levels Bypass Utility")
    print("=============================================")
    print("Usage:")
    print("  python force_bypass_levels.py <index|option> <symbol> <high> <low> [strike] [opt_type]")
    print("")
    print("Examples:")
    print("  1. Bypass NIFTY index spot 9:15 levels:")
    print("     python force_bypass_levels.py index NIFTY 23500.50 23410.20")
    print("  2. Bypass NIFTY 23550 CE option strike levels:")
    print("     python force_bypass_levels.py option NIFTY 179.30 107.00 23550 CE")
    print("")

def run():
    if len(sys.argv) < 5:
        show_usage()
        # Interactive mode if not enough arguments
        print("Switching to interactive mode...")
        mode = input("Enter mode (index/option): ").strip().lower()
        symbol = input("Enter Symbol (e.g. NIFTY, BANKNIFTY): ").strip().upper()
        high = float(input("Enter 9:15 AM High: ").strip())
        low = float(input("Enter 9:15 AM Low: ").strip())
        
        strike = None
        opt_type = None
        if mode == "option":
            strike = int(input("Enter Strike Price: ").strip())
            opt_type = input("Enter Option Type (CE/PE): ").strip().upper()
    else:
        mode = sys.argv[1].lower()
        symbol = sys.argv[2].upper()
        high = float(sys.argv[3])
        low = float(sys.argv[4])
        
        strike = None
        opt_type = None
        if mode == "option":
            if len(sys.argv) < 7:
                print("❌ Error: Strike and Option Type (CE/PE) are required for option mode.")
                sys.exit(1)
            strike = int(sys.argv[5])
            opt_type = sys.argv[6].upper()

    payload = {
        "symbol": symbol,
        "high": high,
        "low": low
    }
    if strike is not None:
        payload["strike"] = strike
    if opt_type is not None:
        payload["opt_type"] = opt_type

    print(f"Sending bypass request for {symbol} (mode={mode})...")
    try:
        url = "http://127.0.0.1:5000/api/bypass-levels"
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            print("✅ SUCCESS (API):", resp.json().get("message"))
            return
        else:
            print(f"⚠️ API failed with code {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Could not contact running Flask server ({e}). Updating local files directly...")

    # Direct fallback file update if server is not running
    json_path = "gvn_recorded_915_ohlc.json"
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
            
    data["date"] = today_str
    if symbol not in data:
        data[symbol] = {}
        
    if mode == "option" and strike and opt_type:
        strike_key = f"{strike} {opt_type}"
        data[symbol][strike_key] = {
            "high": high,
            "low": low,
            "timestamp": datetime.now().isoformat()
        }
        print(f"✅ Updated JSON file {json_path} for {symbol} {strike_key}: High={high}, Low={low}")
        
        # Calculate correct GVN levels
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
        
        # Update SQLite databases directly
        db_paths = ["gvn_master.db", "gvn_data_bank.db"]
        import sqlite3
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='option_915_benchmarks'")
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE option_915_benchmarks 
                            SET high = ?, low = ?, i1 = ?, i5 = ?, i7 = ?
                            WHERE symbol = ? AND strike = ? AND option_type = ? AND date(timestamp) = ?
                        """, (high, low, i1, i5, i7, symbol, float(strike), opt_type, today_str))
                        
                        if cursor.rowcount == 0:
                            cursor.execute("""
                                INSERT INTO option_915_benchmarks (timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7)
                                VALUES (?, ?, ?, ?, ?, ?, 0.5, ?, ?, ?)
                            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, float(strike), opt_type, high, low, i1, i5, i7))
                        conn.commit()
                        print(f"✅ Updated option_915_benchmarks in database: {db_path}")
                    conn.close()
                except Exception as ex:
                    print(f"❌ Error updating db {db_path}: {ex}")
    else:
        spot_key = f"{symbol}_SPOT"
        data[symbol][spot_key] = {
            "high": high,
            "low": low,
            "timestamp": datetime.now().isoformat()
        }
        if symbol == "NIFTY":
            data[symbol]["NIFTY_SPOT"] = {
                "high": high,
                "low": low,
                "timestamp": datetime.now().isoformat()
            }
        print(f"✅ Updated JSON file {json_path} for {symbol}_SPOT: High={high}, Low={low}")
        
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as ex:
        print(f"❌ Error writing to {json_path}: {ex}")

if __name__ == "__main__":
    run()
