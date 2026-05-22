import json
import sqlite3
import os
from datetime import datetime

def update_23550_ce():
    today_str = datetime.now().strftime("%Y-%m-%d")
    ce_high = 364.75
    ce_low = 320.10
    
    # 1. Update JSON File
    json_path = "gvn_recorded_915_ohlc.json"
    data = {}
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            try:
                data = json.load(f)
            except:
                data = {}
                
    data["date"] = today_str
    if "NIFTY" not in data:
        data["NIFTY"] = {}
        
    data["NIFTY"]["23550 CE"] = {
        "high": ce_high,
        "low": ce_low,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4)
    print(f"SUCCESS: Updated {json_path} with High={ce_high}, Low={ce_low}")
    
    # Calculate correct GVN levels using the nse_option_chain logic
    diff = ce_high - ce_low
    result = diff / 2
    n1 = ce_high + result
    n2 = ce_low + result
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    i1 = round(gvn100, 2)
    i5 = round(gvn0 + 0.5 * gvnR, 2)
    i7 = round(gvn0 + 0.220 * gvnR, 2)
    
    # 2. Update SQLite Database
    db_paths = ["gvn_master.db", "gvn_data_bank.db"]
    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Check if table option_915_benchmarks exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='option_915_benchmarks'")
                if cursor.fetchone():
                    # Update existing entries for today or insert
                    cursor.execute("""
                        UPDATE option_915_benchmarks 
                        SET high = ?, low = ?, i1 = ?, i5 = ?, i7 = ?
                        WHERE strike = 23550.0 AND option_type = 'CE' AND date(timestamp) = ?
                    """, (ce_high, ce_low, i1, i5, i7, today_str))
                    
                    # If no row was updated, insert it
                    if cursor.rowcount == 0:
                        cursor.execute("""
                            INSERT INTO option_915_benchmarks (timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7)
                            VALUES (?, 'NIFTY', 23550.0, 'CE', ?, ?, 0.65, ?, ?, ?)
                        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ce_high, ce_low, i1, i5, i7))
                    conn.commit()
                    print(f"SUCCESS: Updated option_915_benchmarks in {db_path} to High={ce_high}, Low={ce_low}")
                conn.close()
            except Exception as e:
                print(f"WARNING: Error updating {db_path}: {e}")

if __name__ == "__main__":
    update_23550_ce()
