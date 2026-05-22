import sys
import os
import json
import sqlite3
from datetime import datetime

# Reconfigure stdout/stderr to use UTF-8 to prevent encoding crashes on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nse_option_chain import get_angel_token, find_angel_token_and_segment, get_915_candle_angel, calculate_gvn_levels
import gvn_data_bank

def main():
    print("=== FORCE REAL ANGEL LEVELS UPDATE ===")
    
    # 1. Load today's recorded JSON file
    json_path = "gvn_recorded_915_ohlc.json"
    if not os.path.exists(json_path):
        print(f"Error: JSON file {json_path} does not exist. Run app or webhook first.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    if data.get("date") != today_str:
        print(f"JSON date is {data.get('date')} but today is {today_str}. Adjusting date.")
        data["date"] = today_str
        
    nifty_options = data.get("NIFTY", {})
    updated_count = 0
    
    # 2. Iterate through strikes looking for 100/90 placeholders
    for strike_key, val in list(nifty_options.items()):
        high = val.get("high")
        low = val.get("low")
        
        # If it matches the 100.0/90.0 placeholder, retrieve the real candle
        if (high == 100.0 and low == 90.0) or high is None or low is None:
            # Parse strike and opt_type from key, e.g. "23350 CE"
            parts = strike_key.split()
            if len(parts) != 2:
                continue
            strike_val = int(parts[0])
            opt_type = parts[1]
            
            print(f"\n🔍 Found placeholder for NIFTY {strike_val} {opt_type}. Fetching real candle from Angel One...")
            
            try:
                # Use nse_option_chain functions to fetch candle from Angel One
                candle = get_915_candle_angel("NIFTY", strike_val, opt_type)
                if candle and candle.get("high") and candle.get("low"):
                    real_high = candle["high"]
                    real_low = candle["low"]
                    print(f"✅ Retrieved NIFTY {strike_val} {opt_type}: High={real_high}, Low={real_low}")
                    
                    # Update local JSON data structure
                    nifty_options[strike_key] = {
                        "high": real_high,
                        "low": real_low,
                        "timestamp": datetime.now().isoformat()
                    }
                    updated_count += 1
                    
                    # Re-calculate levels and save to DB
                    levels = calculate_gvn_levels(real_high, real_low)
                    if levels:
                        # Save to both databases
                        db_paths = ["gvn_master.db", "gvn_data_bank.db"]
                        for db_path in db_paths:
                            if os.path.exists(db_path):
                                try:
                                    conn = sqlite3.connect(db_path)
                                    cursor = conn.cursor()
                                    
                                    # Ensure table exists
                                    cursor.execute('''
                                        CREATE TABLE IF NOT EXISTS option_915_benchmarks (
                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                            symbol TEXT,
                                            strike FLOAT,
                                            option_type TEXT,
                                            high FLOAT,
                                            low FLOAT,
                                            delta FLOAT,
                                            i1 FLOAT,
                                            i5 FLOAT,
                                            i7 FLOAT
                                        )
                                    ''')
                                    
                                    # Update or Insert
                                    cursor.execute("""
                                        UPDATE option_915_benchmarks 
                                        SET high = ?, low = ?, i1 = ?, i5 = ?, i7 = ?
                                        WHERE strike = ? AND option_type = ? AND symbol = 'NIFTY' AND date(timestamp) = ?
                                    """, (real_high, real_low, levels.get("i1"), levels.get("i5"), levels.get("i7"), float(strike_val), opt_type, today_str))
                                    
                                    if cursor.rowcount == 0:
                                        cursor.execute("""
                                            INSERT INTO option_915_benchmarks 
                                            (timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7)
                                            VALUES (?, 'NIFTY', ?, ?, ?, ?, 0.65, ?, ?, ?)
                                        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), float(strike_val), opt_type, real_high, real_low, levels.get("i1"), levels.get("i5"), levels.get("i7")))
                                    
                                    conn.commit()
                                    conn.close()
                                    print(f"💾 Updated DB {db_path} for NIFTY {strike_val} {opt_type}")
                                except Exception as db_err:
                                    print(f"⚠️ Error updating database {db_path}: {db_err}")
                else:
                    print(f"⚠️ Could not fetch candle data for NIFTY {strike_val} {opt_type}")
            except Exception as e:
                print(f"❌ Exception fetching NIFTY {strike_val} {opt_type}: {e}")
                
    if updated_count > 0:
        # Save JSON file
        data["NIFTY"] = nifty_options
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"\n🎉 Successfully corrected {updated_count} strike placeholder levels in JSON and DBs!")
    else:
        print("\nNo placeholder levels required correction.")

if __name__ == "__main__":
    main()
