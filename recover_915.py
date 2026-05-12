
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from truedata_rest_api import TrueDataRestAPI

def recover_915_levels():
    print("🚀 GVN RECOVERY: Fetching 9:15 AM Levels from TrueData History...")
    
    api = TrueDataRestAPI(
        username=os.getenv("TRUEDATA_USERNAME"), 
        password=os.getenv("TRUEDATA_PASSWORD")
    )
    
    # Authenticate
    if not api.login():
        print("❌ TrueData Login Failed. Check credentials in .env")
        return

    # Today's date in TrueData format: YYMMDDHHMMSS
    # 2026-05-12 09:15:00 -> 260512091500
    today_str = datetime.now().strftime("%y%m%d")
    from_dt = f"{today_str}091500"
    to_dt = f"{today_str}092000"
    
    print(f"📡 Fetching History for NIFTY from {from_dt} to {to_dt}...")
    
    # Fetch 1-min candles for Nifty 50 Index
    # In TrueData, Nifty index symbol is typically "NIFTY 50" or "NIFTY-I"
    # We'll try common variations
    res = api.get_historical_data("NIFTY 50", from_dt, to_dt, resolution="1")
    
    if not res or "records" not in res:
        print("⚠️ 'NIFTY 50' failed. Trying 'NIFTY'...")
        res = api.get_historical_data("NIFTY", from_dt, to_dt, resolution="1")

    if res and "records" in res:
        candles = res["records"]
        if candles:
            highs = [float(c[2]) for c in candles] # index 2 is High in TrueData history format
            lows = [float(c[3]) for c in candles]  # index 3 is Low
            
            day_high = max(highs)
            day_low = min(lows)
            
            print(f"✅ FOUND LEVELS for Today (May 12, 2026):")
            print(f"   9:15 AM HIGH: {day_high}")
            print(f"   9:15 AM LOW:  {day_low}")
            
            # Save to a recovery file
            import json
            recovery_data = {
                "symbol": "NIFTY",
                "high": day_high,
                "low": day_low,
                "captured": True,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open("gvn_915_recovery.json", "w") as f:
                json.dump(recovery_data, f)
            print("💾 Levels saved to gvn_915_recovery.json. System will now pick them up.")
        else:
            print("❌ No candles found for the 9:15-9:20 window.")
    else:
        print(f"❌ Failed to fetch historical data: {res}")

if __name__ == "__main__":
    recover_915_levels()
