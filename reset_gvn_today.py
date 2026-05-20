import json
import sqlite3
import os
from datetime import datetime

def reset_today():
    print("[RESET] Resetting GVN 915 AM OHLC cache for today (20-May-2026)...")
    
    # 1. Update gvn_recorded_915_ohlc.json with correct values
    correct_ohlc = {
        "date": "2026-05-20",
        "NIFTY": {
            "23650 CE": {
                "high": 137.50,
                "low": 100.40,
                "timestamp": datetime.now().isoformat()
            },
            "23750 PE": {
                "high": 440.00,
                "low": 390.80,
                "timestamp": datetime.now().isoformat()
            }
        }
    }
    
    with open("gvn_recorded_915_ohlc.json", "w") as f:
        json.dump(correct_ohlc, f, indent=4)
    print("SUCCESS: Overwrote gvn_recorded_915_ohlc.json with correct TV High/Low values.")
    
    # 2. Reset database records for today to avoid stale cache
    if os.path.exists("gvn_master.db"):
        try:
            conn = sqlite3.connect("gvn_master.db")
            cursor = conn.cursor()
            # Clear stored option benchmarks for today
            cursor.execute("DELETE FROM option_benchmarks WHERE date_val = '2026-05-20'")
            # Clear cached signals for today
            cursor.execute("DELETE FROM signals WHERE date_val = '2026-05-20'")
            conn.commit()
            conn.close()
            print("SUCCESS: Cleared database cache for today (option_benchmarks and signals).")
        except Exception as e:
            print(f"WARNING: Database clean error: {e}")
            
    print("\nRESET COMPLETED SUCCESSFULLY! You can now start the GVN Master Algo.")

if __name__ == "__main__":
    reset_today()
