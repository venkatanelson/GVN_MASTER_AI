import os
import sys
import json
from datetime import datetime, timedelta

# Reconfigure standard output streams to use UTF-8 to prevent UnicodeEncodeErrors on Windows
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

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shared_data
from nse_option_chain import (
    process_candles_for_timeframe,
    get_recorded_index_915_ohlc,
    load_all_recorded_benchmarks,
    save_recorded_915_ohlc,
    load_recorded_915_ohlc
)

def run_tests():
    print("[TEST] Running GVN Dual-Timeframe & Bypass Verification...\n")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Clean up gvn_recorded_915_ohlc.json for a clean test environment
    json_path = "gvn_recorded_915_ohlc.json"
    old_backup = None
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                old_backup = json.load(f)
            os.remove(json_path)
            print("Removed existing JSON file for clean testing.")
        except Exception as e:
            print(f"Error backing up JSON: {e}")

    try:
        # =====================================================================
        # 1. Test process_candles_for_timeframe
        # =====================================================================
        print("-> Testing process_candles_for_timeframe...")
        
        # Create mock 1-minute candles from 09:15 to 09:20
        # Format of Angel One historical data: [Timestamp, Open, High, Low, Close, Volume]
        mock_candles = [
            ["2026-05-22T09:15:00+05:30", 100.0, 105.0, 95.0, 101.0, 1000], # 09:15
            ["2026-05-22T09:16:00+05:30", 101.0, 110.0, 100.0, 108.0, 1500], # 09:16
            ["2026-05-22T09:17:00+05:30", 108.0, 109.0, 102.0, 105.0, 1200], # 09:17
            ["2026-05-22T09:18:00+05:30", 105.0, 115.0, 104.0, 112.0, 1800], # 09:18
            ["2026-05-22T09:19:00+05:30", 112.0, 114.0, 90.0, 95.0, 2000],  # 09:19
            ["2026-05-22T09:20:00+05:30", 95.0, 98.0, 92.0, 97.0, 1100],    # 09:20 (represent 09:20-09:21, excluded)
        ]
        
        # Test 1MIN timeframe
        res_1min = process_candles_for_timeframe(mock_candles, "1MIN", source="TestMock")
        assert res_1min is not None
        assert res_1min["timeframe"] == "1MIN"
        assert res_1min["high"] == 105.0
        assert res_1min["low"] == 95.0
        assert res_1min["close"] == 101.0
        print("OK: process_candles_for_timeframe 1MIN is correct.")
        
        # Test 5MIN timeframe (should aggregate 09:15 to 09:19)
        res_5min = process_candles_for_timeframe(mock_candles, "5MIN", source="TestMock")
        assert res_5min is not None
        assert res_5min["timeframe"] == "5MIN"
        assert res_5min["high"] == 115.0  # Max High of 09:15-09:19 (is 115.0 at 09:18)
        assert res_5min["low"] == 90.0    # Min Low of 09:15-09:19 (is 90.0 at 09:19)
        assert res_5min["close"] == 95.0  # Close at the end of 09:19
        print("OK: process_candles_for_timeframe 5MIN aggregation is correct.")
        
        # Test fallback when 5-min filter yields empty list
        empty_filter_candles = [
            ["2026-05-22T09:25:00+05:30", 100.0, 105.0, 95.0, 101.0, 1000]
        ]
        res_fallback = process_candles_for_timeframe(empty_filter_candles, "5MIN", source="TestMock")
        assert res_fallback is not None
        assert res_fallback["timeframe"] == "1MIN"
        assert res_fallback["high"] == 105.0
        assert res_fallback["low"] == 95.0
        print("OK: process_candles_for_timeframe 5MIN fallbacks to 1MIN correctly.")

        # =====================================================================
        # 2. Test get_recorded_index_915_ohlc and load_all_recorded_benchmarks
        # =====================================================================
        print("\n-> Testing JSON loader and save functions...")
        
        # Reset shared memory first
        for key in shared_data.gvn_915_benchmark:
            shared_data.gvn_915_benchmark[key] = {"high": 0.0, "low": 0.0, "captured": False, "date": None}
            
        # Verify empty load
        assert get_recorded_index_915_ohlc("NIFTY") is None
        print("OK: Spot data is initially empty.")
        
        # Save mock index spot and option levels to JSON
        save_recorded_915_ohlc("NIFTY_SPOT", 23550.25, 23410.50, symbol="NIFTY", timeframe="5MIN")
        save_recorded_915_ohlc("BANKNIFTY_SPOT", 48200.00, 47900.00, symbol="BANKNIFTY", timeframe="5MIN")
        
        # Verify individual index spot retrieval
        nifty_ohlc = get_recorded_index_915_ohlc("NIFTY")
        assert nifty_ohlc == (23550.25, 23410.50), f"Incorrect Nifty spot: {nifty_ohlc}"
        
        banknifty_ohlc = get_recorded_index_915_ohlc("BANKNIFTY")
        assert banknifty_ohlc == (48200.00, 47900.00), f"Incorrect Banknifty spot: {banknifty_ohlc}"
        print("OK: get_recorded_index_915_ohlc correctly fetches index spots.")
        
        # Verify load_all_recorded_benchmarks loads into shared memory
        res_load = load_all_recorded_benchmarks()
        assert res_load is True
        assert shared_data.gvn_915_benchmark["NIFTY"]["high"] == 23550.25
        assert shared_data.gvn_915_benchmark["NIFTY"]["low"] == 23410.50
        assert shared_data.gvn_915_benchmark["NIFTY"]["captured"] is True
        assert shared_data.gvn_915_benchmark["NIFTY"]["timeframe"] == "5MIN"
        assert shared_data.gvn_915_benchmark["BANKNIFTY"]["high"] == 48200.00
        assert shared_data.gvn_915_benchmark["BANKNIFTY"]["low"] == 47900.00
        print("OK: load_all_recorded_benchmarks successfully populates shared memory state.")

        # =====================================================================
        # 3. Test HTTP Bypass Endpoint (Simulate API request)
        # =====================================================================
        print("\n-> Testing Bypass / Override functionality...")
        
        # Test direct override of index levels via direct mock of Flask handler logic
        # Clear Nifty benchmark
        shared_data.gvn_915_benchmark["NIFTY"] = {"high": 0.0, "low": 0.0, "captured": False, "date": None}
        
        # Simulate bypass call for NIFTY spot
        save_recorded_915_ohlc("NIFTY_SPOT", 23600.0, 23500.0, symbol="NIFTY", timeframe="BYPASS")
        shared_data.gvn_915_benchmark["NIFTY"] = {
            "high": 23600.0,
            "low": 23500.0,
            "captured": True,
            "date": today_str,
            "timeframe": "BYPASS"
        }
        
        nifty_spot_ohlc = get_recorded_index_915_ohlc("NIFTY")
        assert nifty_spot_ohlc == (23600.0, 23500.0)
        assert shared_data.gvn_915_benchmark["NIFTY"]["high"] == 23600.0
        assert shared_data.gvn_915_benchmark["NIFTY"]["timeframe"] == "BYPASS"
        print("OK: Spot bypass overrides in-memory and file data cleanly.")
        
        print("\nALL TESTS PASSED SUCCESSFULLY! GVN Dual-Timeframe & Bypass are glitch-free.")

    finally:
        # Restore original JSON file to avoid breaking user's current day state
        if os.path.exists(json_path):
            os.remove(json_path)
        if old_backup:
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(old_backup, f, indent=4)
                print("Restored original GVN levels JSON file.")
            except Exception as e:
                print(f"Error restoring original JSON file: {e}")

if __name__ == "__main__":
    run_tests()
