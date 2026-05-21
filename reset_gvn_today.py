import json
import sqlite3
import os
from datetime import datetime

def reset_today():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"==================================================")
    print(f"🔄 GVN ALGO RESET UTILITY - DATE: {today_str} 🚀")
    print(f"==================================================")
    
    # 1. Ask for 23550 CE correct High / Low
    print("\n👉 Please enter the correct 9:15 AM candle OHLC values from TradingView:")
    try:
        ce_high = float(input("Enter 23550 CE High (e.g. 364.75): ") or "364.75")
        ce_low = float(input("Enter 23550 CE Low (e.g. 183.55): ") or "183.55")
        
        pe_high = float(input("Enter 23750 PE High (e.g. 440.0): ") or "100.0")
        pe_low = float(input("Enter 23750 PE Low (e.g. 390.0): ") or "90.0")
    except ValueError:
        print("❌ Invalid input! Using defaults.")
        ce_high, ce_low = 364.75, 183.55
        pe_high, pe_low = 100.0, 90.0

    # 2. Prepare the JSON data structure
    correct_ohlc = {
        "date": today_str,
        "NIFTY": {
            "23550 CE": {
                "high": ce_high,
                "low": ce_low,
                "timestamp": datetime.now().isoformat()
            },
            "23750 PE": {
                "high": pe_high,
                "low": pe_low,
                "timestamp": datetime.now().isoformat()
            }
        }
    }
    
    # Write to json file
    with open("gvn_recorded_915_ohlc.json", "w") as f:
        json.dump(correct_ohlc, f, indent=4)
    print(f"\n✅ SUCCESS: Overwrote gvn_recorded_915_ohlc.json with correct values:")
    print(f"   - 23550 CE: High={ce_high}, Low={ce_low}")
    print(f"   - 23750 PE: High={pe_high}, Low={pe_low}")
    
    # 3. Clear database cache to prevent stale calculations
    db_paths = ["gvn_master.db", "gvn_data_bank.db"]
    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Clear stored option benchmarks for today
                cursor.execute("DELETE FROM option_915_benchmarks WHERE date(timestamp) = ?", (today_str,))
                # Also try index benchmarks table if it exists
                try:
                    cursor.execute("DELETE FROM option_benchmarks WHERE date(timestamp) = ?", (today_str,))
                except: pass
                conn.commit()
                conn.close()
                print(f"✅ SUCCESS: Cleared database cache for today in {db_path}.")
            except Exception as e:
                print(f"⚠️ Database clean warning for {db_path}: {e}")
                
    print("\n🎉 RESET COMPLETED! You can now restart the app.py program.")
    print("==================================================")

if __name__ == "__main__":
    reset_today()
