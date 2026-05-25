import os
import sys
import json
import time
from datetime import datetime, time as datetime_time

# Add parent directory to path to import nse_option_chain
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nse_option_chain

def run_test():
    print("[TEST] Starting Automated Test for NSE 9:15 AM Candle Tracker...")
    
    # 1. Mock Option Chain Response
    mock_nifty_records = {
        "records": {
            "underlyingValue": 23600.0,
            "data": [
                {
                    "strikePrice": 23600,
                    "CE": {"lastPrice": 150.0},
                    "PE": {"lastPrice": 120.0}
                },
                {
                    "strikePrice": 23550,
                    "CE": {"lastPrice": 180.0},
                    "PE": {"lastPrice": 95.0}
                }
            ]
        }
    }
    
    # Backup original fetch function
    orig_fetch = nse_option_chain.fetch_from_nse_direct
    
    # Mock fetch_from_nse_direct
    def mock_fetch(symbol):
        print(f"   [Mock Fetch] Fetching for {symbol}...")
        return mock_nifty_records
        
    nse_option_chain.fetch_from_nse_direct = mock_fetch
    
    # 2. Test live tracking poll during 9:15 - 9:20 AM window
    print("[TEST] Simulating 9:15 AM Live Poll...")
    # Clear any previous temp data
    nse_option_chain.nse_running_915_ohlc_temp.clear()
    
    # Simulate a poll
    symbol = "NIFTY"
    data = nse_option_chain.fetch_from_nse_direct(symbol)
    records = data["records"]
    spot = float(records.get("underlyingValue", 0))
    
    spot_key = f"{symbol}_SPOT"
    nse_option_chain.nse_running_915_ohlc_temp[spot_key] = {"high": spot, "low": spot}
    
    step = 50
    atm = round(spot / step) * step
    tracked_strikes = [int(atm + i * step) for i in range(-5, 6)]
    
    for item in records.get("data", []):
        strike_val = int(item.get("strikePrice", 0))
        if strike_val in tracked_strikes:
            for opt_type in ["CE", "PE"]:
                opt_item = item.get(opt_type)
                if opt_item:
                    ltp = float(opt_item.get("lastPrice", 0))
                    if ltp > 0:
                        strike_key = f"{strike_val} {opt_type}"
                        if symbol not in nse_option_chain.nse_running_915_ohlc_temp:
                            nse_option_chain.nse_running_915_ohlc_temp[symbol] = {}
                        nse_option_chain.nse_running_915_ohlc_temp[symbol][strike_key] = {"high": ltp, "low": ltp}
                        
    # Simulate a second poll with different prices to test high/low logic
    print("[TEST] Simulating 9:16 AM Live Poll with new prices...")
    mock_nifty_records["records"]["underlyingValue"] = 23620.0
    mock_nifty_records["records"]["data"][0]["CE"]["lastPrice"] = 160.0 # Higher high
    mock_nifty_records["records"]["data"][0]["PE"]["lastPrice"] = 110.0 # Lower low
    
    data = nse_option_chain.fetch_from_nse_direct(symbol)
    records = data["records"]
    spot = float(records.get("underlyingValue", 0))
    
    # Update running spot high/low
    nse_option_chain.nse_running_915_ohlc_temp[spot_key]["high"] = max(nse_option_chain.nse_running_915_ohlc_temp[spot_key]["high"], spot)
    nse_option_chain.nse_running_915_ohlc_temp[spot_key]["low"] = min(nse_option_chain.nse_running_915_ohlc_temp[spot_key]["low"], spot)
    
    for item in records.get("data", []):
        strike_val = int(item.get("strikePrice", 0))
        if strike_val in tracked_strikes:
            for opt_type in ["CE", "PE"]:
                opt_item = item.get(opt_type)
                if opt_item:
                    ltp = float(opt_item.get("lastPrice", 0))
                    if ltp > 0:
                        strike_key = f"{strike_val} {opt_type}"
                        if strike_key in nse_option_chain.nse_running_915_ohlc_temp[symbol]:
                            nse_option_chain.nse_running_915_ohlc_temp[symbol][strike_key]["high"] = max(nse_option_chain.nse_running_915_ohlc_temp[symbol][strike_key]["high"], ltp)
                            nse_option_chain.nse_running_915_ohlc_temp[symbol][strike_key]["low"] = min(nse_option_chain.nse_running_915_ohlc_temp[symbol][strike_key]["low"], ltp)
                            
    # Verify temp tracking data is correct
    print("[TEST] Verifying Temp Tracking Data...")
    print(f"   Spot High: {nse_option_chain.nse_running_915_ohlc_temp[spot_key]['high']} (Expected: 23620.0)")
    print(f"   Spot Low: {nse_option_chain.nse_running_915_ohlc_temp[spot_key]['low']} (Expected: 23600.0)")
    print(f"   CE 23600 High: {nse_option_chain.nse_running_915_ohlc_temp[symbol]['23600 CE']['high']} (Expected: 160.0)")
    print(f"   CE 23600 Low: {nse_option_chain.nse_running_915_ohlc_temp[symbol]['23600 CE']['low']} (Expected: 150.0)")
    print(f"   PE 23600 High: {nse_option_chain.nse_running_915_ohlc_temp[symbol]['23600 PE']['high']} (Expected: 120.0)")
    print(f"   PE 23600 Low: {nse_option_chain.nse_running_915_ohlc_temp[symbol]['23600 PE']['low']} (Expected: 110.0)")
    
    assert nse_option_chain.nse_running_915_ohlc_temp[spot_key]["high"] == 23620.0
    assert nse_option_chain.nse_running_915_ohlc_temp[spot_key]["low"] == 23600.0
    assert nse_option_chain.nse_running_915_ohlc_temp[symbol]["23600 CE"]["high"] == 160.0
    assert nse_option_chain.nse_running_915_ohlc_temp[symbol]["23600 CE"]["low"] == 150.0
    assert nse_option_chain.nse_running_915_ohlc_temp[symbol]["23600 PE"]["high"] == 120.0
    assert nse_option_chain.nse_running_915_ohlc_temp[symbol]["23600 PE"]["low"] == 110.0
    
    # 3. Simulate Finalization at 9:20 AM
    print("[TEST] Simulating Finalization at 9:20 AM...")
    
    # Backup actual recorded file if exists
    backup_file = "gvn_recorded_915_ohlc.json.bak"
    if os.path.exists("gvn_recorded_915_ohlc.json"):
        os.rename("gvn_recorded_915_ohlc.json", backup_file)
        print("   [Backup] Created backup of gvn_recorded_915_ohlc.json")
        
    try:
        recorded_data = nse_option_chain.load_recorded_915_ohlc()
        today_str = datetime.now().strftime("%Y-%m-%d")
        recorded_data["date"] = today_str
        
        # Run finalization logic on temp data
        for sym in ["NIFTY"]:
            spot_key = f"{sym}_SPOT"
            if spot_key in nse_option_chain.nse_running_915_ohlc_temp:
                spot_data = nse_option_chain.nse_running_915_ohlc_temp[spot_key]
                if sym not in recorded_data:
                    recorded_data[sym] = {}
                recorded_data[sym][spot_key] = {
                    "high": round(spot_data["high"], 2),
                    "low": round(spot_data["low"], 2),
                    "timestamp": datetime.now().isoformat(),
                    "source": "NSE_WEBSITE_LIVE_TRACK"
                }
            
            if sym in nse_option_chain.nse_running_915_ohlc_temp:
                for strike_key, strike_data in nse_option_chain.nse_running_915_ohlc_temp[sym].items():
                    if sym not in recorded_data:
                        recorded_data[sym] = {}
                    recorded_data[sym][strike_key] = {
                        "high": round(strike_data["high"], 2),
                        "low": round(strike_data["low"], 2),
                        "timestamp": datetime.now().isoformat(),
                        "source": "NSE_WEBSITE_LIVE_TRACK"
                    }
                    
        with open("gvn_recorded_915_ohlc.json", "w", encoding="utf-8") as f:
            json.dump(recorded_data, f, indent=4)
            
        # Verify JSON file has been written correctly
        print("[TEST] Verifying persistent JSON content...")
        with open("gvn_recorded_915_ohlc.json", "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            
        print(f"   Date: {saved_data.get('date')}")
        print(f"   Saved Spot High: {saved_data['NIFTY']['NIFTY_SPOT']['high']}")
        print(f"   Saved 23600 CE High: {saved_data['NIFTY']['23600 CE']['high']}")
        print(f"   Saved 23600 CE Low: {saved_data['NIFTY']['23600 CE']['low']}")
        
        assert saved_data["NIFTY"]["NIFTY_SPOT"]["high"] == 23620.0
        assert saved_data["NIFTY"]["23600 CE"]["high"] == 160.0
        assert saved_data["NIFTY"]["23600 CE"]["low"] == 150.0
        
        # Test loading logic falls back correctly
        print("[TEST] Testing retrieval logic get_recorded_index_915_ohlc...")
        ohlc = nse_option_chain.get_recorded_index_915_ohlc("NIFTY")
        print(f"   Index OHLC retrieved: {ohlc}")
        assert ohlc == (23620.0, 23600.0)
        
        print("[TEST] Testing retrieval logic get_real_option_915_ohlc...")
        opt_ohlc = nse_option_chain.get_real_option_915_ohlc("NIFTY", 23600, "CE")
        print(f"   Option OHLC retrieved: {opt_ohlc}")
        assert opt_ohlc == (160.0, 150.0)
        
        print("[TEST] ALL TESTS PASSED SUCCESSFULLY!")
        
    finally:
        # Cleanup test file
        if os.path.exists("gvn_recorded_915_ohlc.json"):
            os.remove("gvn_recorded_915_ohlc.json")
        # Restore backup
        if os.path.exists(backup_file):
            os.rename(backup_file, "gvn_recorded_915_ohlc.json")
            print("   [Backup] Restored original gvn_recorded_915_ohlc.json")
            
    # Restore original fetch function
    nse_option_chain.fetch_from_nse_direct = orig_fetch

if __name__ == "__main__":
    run_test()
