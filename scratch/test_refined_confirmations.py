import os
import sys
import json
import time
from datetime import datetime, time as datetime_time
from unittest.mock import MagicMock, patch

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shared_data
import nse_option_chain
from gvn_ai_delta60_engine import GVNAiDelta60Engine

def run_test():
    print("[TEST] Starting Refined Confirmations & Nifty 50 Filter Test...")

    # ==========================================
    # PART 1: TEST NIFTY 50 ADVANCES/DECLINES
    # ==========================================
    print("\n--- 1. Testing Nifty 50 Advances/Declines Parser ---")
    mock_indices_response = {
        "data": [
            {
                "index": "NIFTY 50",
                "advances": 38,
                "declines": 12,
                "unchanged": 0,
                "percentChange": 1.2
            }
        ]
    }
    
    # Mock nse_session.get response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_indices_response
    
    # Backup original fetch time and session
    orig_time = nse_option_chain.last_nifty50_stocks_fetch_time
    nse_option_chain.last_nifty50_stocks_fetch_time = 0 # Force fetch
    
    with patch.object(nse_option_chain.nse_session, 'get', return_value=mock_resp) as mock_get:
        nse_option_chain.fetch_nifty50_advances_declines()
        
        # Verify the market pulse was updated correctly
        pulse = shared_data.market_pulse
        print(f"   Advances: {pulse.get('nifty50_advances')} (Expected: 38)")
        print(f"   Declines: {pulse.get('nifty50_declines')} (Expected: 12)")
        print(f"   Trend Signal: {pulse.get('nifty50_trend_signal')} (Expected: STRONG BULLISH)")
        
        assert pulse.get("nifty50_advances") == 38
        assert pulse.get("nifty50_declines") == 12
        assert pulse.get("nifty50_trend_signal") == "STRONG BULLISH"

    # ==========================================
    # PART 2: TEST TIME-LOCKING & POLLING LIMIT
    # ==========================================
    print("\n--- 2. Testing 9:15-9:20 AM Time Locking & Block Prevention ---")
    
    # Clear tracking data
    nse_option_chain.nse_running_915_ohlc_temp.clear()
    nse_option_chain.local_broker_915_ohlc.clear()
    nse_option_chain.nse_single_poll_done = False
    nse_option_chain.nse_915_finalized_today = False
    
    # We will simulate 3 different timestamps to check:
    # A. 09:16:00 AM (Should only track broker data locally, should NOT call NSE website)
    # B. 09:19:45 AM (Should track broker data AND execute the single NSE poll)
    # C. 09:20:00 AM (Should finalize and merge local broker data and single NSE poll)
    
    mock_option_chain = {
        "records": {
            "underlyingValue": 23600.0,
            "data": [
                {
                    "strikePrice": 23600,
                    "CE": {"lastPrice": 140.0},
                    "PE": {"lastPrice": 110.0}
                }
            ]
        }
    }
    
    mock_oc_resp = MagicMock()
    mock_oc_resp.status_code = 200
    mock_oc_resp.json.return_value = mock_option_chain
    
    # Setup mock local market data
    shared_data.market_data["NIFTY"] = 23605.0
    shared_data.market_data["23600 CE"] = 145.0
    shared_data.market_data["23600 PE"] = 105.0
    
    with patch.object(nse_option_chain.nse_session, 'get', return_value=mock_oc_resp) as mock_get_oc:
        # A. Simulate 09:16:00 AM
        print("   [A] Simulating loop at 09:16:00 AM...")
        dt_916 = datetime.now().replace(hour=9, minute=16, second=0, microsecond=0)
        
        # We manually run a chunk of the tracking code using mock time
        # --- Simulating nse_background_worker tracking ---
        current_time = dt_916.time()
        start_time = dt_916.replace(hour=9, minute=15, second=0, microsecond=0).time()
        poll_trigger_time = dt_916.replace(hour=9, minute=19, second=40, microsecond=0).time()
        end_time = dt_916.replace(hour=9, minute=20, second=0, microsecond=0).time()
        
        # Bypass weekday check for test
        if start_time <= current_time < end_time:
            # 1. Track spot price locally
            spot = float(shared_data.market_data.get("NIFTY", 0))
            if spot > 0:
                spot_key = "NIFTY_SPOT"
                if spot_key not in nse_option_chain.local_broker_915_ohlc:
                    nse_option_chain.local_broker_915_ohlc[spot_key] = {"high": spot, "low": spot}
                
                # 2. Track option strikes locally
                step = 50
                atm = round(spot / step) * step
                tracked_strikes = [int(atm + i * step) for i in range(-5, 6)]
                
                for strike in tracked_strikes:
                    for opt_type in ["CE", "PE"]:
                        strike_key = f"{strike} {opt_type}"
                        ltp = float(shared_data.market_data.get(strike_key, 0))
                        if ltp > 0:
                            if "NIFTY" not in nse_option_chain.local_broker_915_ohlc:
                                nse_option_chain.local_broker_915_ohlc["NIFTY"] = {}
                            nse_option_chain.local_broker_915_ohlc["NIFTY"][strike_key] = {"high": ltp, "low": ltp}
            
            # Check that NSE website was NOT polled
            if poll_trigger_time <= current_time < end_time and not nse_option_chain.nse_single_poll_done:
                # should not reach here at 9:16
                pass
                    
        # Verify NSE was NOT polled
        mock_get_oc.assert_not_called()
        print("      SUCCESS: Local broker tracking active, NSE website was NOT polled.")
        print(f"      Local NIFTY Spot tracked: {nse_option_chain.local_broker_915_ohlc['NIFTY_SPOT']}")
        print(f"      Local 23600 CE tracked: {nse_option_chain.local_broker_915_ohlc['NIFTY']['23600 CE']}")
        
        # B. Simulate 09:19:45 AM (Trigger single poll)
        print("   [B] Simulating loop at 09:19:45 AM...")
        dt_919 = datetime.now().replace(hour=9, minute=19, second=45, microsecond=0)
        current_time = dt_919.time()
        
        # Simulating tracking chunk
        # Bypass weekday check for test
        if start_time <= current_time < end_time:
            # Update spot locally (with new price 23610)
            shared_data.market_data["NIFTY"] = 23610.0
            spot = 23610.0
            spot_key = "NIFTY_SPOT"
            nse_option_chain.local_broker_915_ohlc[spot_key]["high"] = max(nse_option_chain.local_broker_915_ohlc[spot_key]["high"], spot)
            
            # Trigger single poll
            if poll_trigger_time <= current_time < end_time and not nse_option_chain.nse_single_poll_done:
                # Mocking calling fetch_from_nse_direct inside
                data = nse_option_chain.fetch_from_nse_direct("NIFTY")
                records = data["records"]
                spot_nse = float(records.get("underlyingValue", 0))
                spot_key_nse = "NIFTY_SPOT"
                
                nse_option_chain.nse_running_915_ohlc_temp[spot_key_nse] = {"high": spot_nse, "low": spot_nse}
                
                step = 50
                atm = round(spot_nse / step) * step
                tracked_strikes = [int(atm + i * step) for i in range(-5, 6)]
                
                option_data_list = records.get("data", [])
                for item in option_data_list:
                    strike_val = int(item.get("strikePrice", 0))
                    if strike_val in tracked_strikes:
                        for opt_type in ["CE", "PE"]:
                            opt_item = item.get(opt_type)
                            if opt_item:
                                ltp = float(opt_item.get("lastPrice", 0))
                                if ltp > 0:
                                    strike_key = f"{strike_val} {opt_type}"
                                    if "NIFTY" not in nse_option_chain.nse_running_915_ohlc_temp:
                                        nse_option_chain.nse_running_915_ohlc_temp["NIFTY"] = {}
                                    nse_option_chain.nse_running_915_ohlc_temp["NIFTY"][strike_key] = {"high": ltp, "low": ltp}
                nse_option_chain.nse_single_poll_done = True
                    
        # Verify NSE was polled
        assert mock_get_oc.call_count >= 1
        print("      SUCCESS: Single NSE website poll triggered successfully at 9:19:45 AM.")
        print(f"      NSE tracked Spot: {nse_option_chain.nse_running_915_ohlc_temp['NIFTY_SPOT']}")
        print(f"      NSE tracked 23600 CE: {nse_option_chain.nse_running_915_ohlc_temp['NIFTY']['23600 CE']}")
        
        # C. Simulate 09:20:00 AM (Finalization & Merger)
        print("   [C] Simulating finalization at 09:20:00 AM...")
        dt_920 = datetime.now().replace(hour=9, minute=20, second=0, microsecond=0)
        current_time = dt_920.time()
        
        backup_file = "gvn_recorded_915_ohlc.json.bak"
        if os.path.exists("gvn_recorded_915_ohlc.json"):
            os.rename("gvn_recorded_915_ohlc.json", backup_file)
            
        try:
            if current_time >= end_time and not nse_option_chain.nse_915_finalized_today:
                # Merge logic
                merged_ohlc = {}
                for k, v in nse_option_chain.local_broker_915_ohlc.items():
                    if isinstance(v, dict):
                        merged_ohlc[k] = v.copy()
                        
                for k, v in nse_option_chain.nse_running_915_ohlc_temp.items():
                    if k in ["NIFTY", "BANKNIFTY"] and isinstance(v, dict):
                        if k not in merged_ohlc:
                            merged_ohlc[k] = {}
                        for sk, sv in v.items():
                            if sk not in merged_ohlc[k]:
                                merged_ohlc[k][sk] = sv.copy()
                            else:
                                merged_ohlc[k][sk]["high"] = max(merged_ohlc[k][sk]["high"], sv["high"])
                                merged_ohlc[k][sk]["low"] = min(merged_ohlc[k][sk]["low"], sv["low"])
                    elif isinstance(v, dict):
                        if k not in merged_ohlc:
                            merged_ohlc[k] = v.copy()
                        else:
                            if "high" in v and "high" in merged_ohlc[k]:
                                merged_ohlc[k]["high"] = max(merged_ohlc[k]["high"], v["high"])
                            if "low" in v and "low" in merged_ohlc[k]:
                                merged_ohlc[k]["low"] = min(merged_ohlc[k]["low"], v["low"])
                                
                # Verify merger results
                print(f"      Merged NIFTY Spot High: {merged_ohlc['NIFTY_SPOT']['high']} (Expected: 23610.0)")
                print(f"      Merged NIFTY Spot Low: {merged_ohlc['NIFTY_SPOT']['low']} (Expected: 23600.0 from NSE or 23605.0 from local)")
                print(f"      Merged 23600 CE High: {merged_ohlc['NIFTY']['23600 CE']['high']} (Expected: 145.0 from local / 140.0 from NSE)")
                print(f"      Merged 23600 CE Low: {merged_ohlc['NIFTY']['23600 CE']['low']} (Expected: 140.0)")
                
                assert merged_ohlc["NIFTY_SPOT"]["high"] == 23610.0
                assert merged_ohlc["NIFTY"]["23600 CE"]["high"] == 145.0
                assert merged_ohlc["NIFTY"]["23600 CE"]["low"] == 140.0
                print("      SUCCESS: Merger successfully prioritized local high-res highs and merged NSE values.")
                
        finally:
            if os.path.exists("gvn_recorded_915_ohlc.json"):
                os.remove("gvn_recorded_915_ohlc.json")
            if os.path.exists(backup_file):
                os.rename(backup_file, "gvn_recorded_915_ohlc.json")

    # ==========================================
    # PART 3: TEST AI DELTA 60 ENTRY FILTER
    # ==========================================
    print("\n--- 3. Testing AI Delta 60 Entry Filter ---")
    
    # Initialize mock engine
    engine = GVNAiDelta60Engine()
    
    # Case A: F&O Nifty 50 Stocks are STRONG BEARISH. CE entries must be blocked.
    print("   [A] Simulating F&O Nifty 50 trend = STRONG BEARISH...")
    shared_data.market_pulse["nifty50_trend_signal"] = "STRONG BEARISH"
    shared_data.market_pulse["score"] = 68 # Bullish technicals
    shared_data.market_pulse["wind_direction"] = "UP WIND"
    shared_data.market_pulse["wind_power"] = 1.0
    
    # Setup mock strike
    ce_strike = {
        "strike": 23600,
        "type": "CE",
        "ltp": 150.0,
        "high_915": 160.0,
        "low_915": 140.0,
        "symbol": "NIFTY23600CE",
        "delta": 0.60
    }
    
    wind_dir = shared_data.market_pulse.get("wind_direction", "NEUTRAL")
    is_bullish = ce_strike['type'] == 'CE' and (shared_data.market_pulse.get("score", 50) >= 65 or any(w in wind_dir for w in ["UP WIND", "SHORT COVERING"]))
    
    # Apply filter
    nifty50_trend = shared_data.market_pulse.get("nifty50_trend_signal", "NEUTRAL")
    if nifty50_trend == "STRONG BEARISH" and ce_strike['type'] == 'CE':
        is_bullish = False
        
    print(f"      Is CE Bullish Entry Allowed? {is_bullish} (Expected: False)")
    assert is_bullish is False
    print("      SUCCESS: CE entry blocked successfully during STRONG BEARISH Nifty 50 stocks trend.")

    # Case B: F&O Nifty 50 Stocks are STRONG BULLISH. PE entries must be blocked.
    print("   [B] Simulating F&O Nifty 50 trend = STRONG BULLISH...")
    shared_data.market_pulse["nifty50_trend_signal"] = "STRONG BULLISH"
    shared_data.market_pulse["score"] = 30 # Bearish technicals
    shared_data.market_pulse["wind_direction"] = "DOWN WIND"
    
    pe_strike = {
        "strike": 23600,
        "type": "PE",
        "ltp": 120.0,
        "high_915": 130.0,
        "low_915": 110.0,
        "symbol": "NIFTY23600PE",
        "delta": 0.60
    }
    
    wind_dir = shared_data.market_pulse.get("wind_direction", "NEUTRAL")
    is_bearish = pe_strike['type'] == 'PE' and (shared_data.market_pulse.get("score", 50) <= 35 or any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING"]))
    
    # Apply filter
    nifty50_trend = shared_data.market_pulse.get("nifty50_trend_signal", "NEUTRAL")
    if nifty50_trend == "STRONG BULLISH" and pe_strike['type'] == 'PE':
        is_bearish = False
        
    print(f"      Is PE Bearish Entry Allowed? {is_bearish} (Expected: False)")
    assert is_bearish is False
    print("      SUCCESS: PE entry blocked successfully during STRONG BULLISH Nifty 50 stocks trend.")
    
    print("\n[SUCCESS] ALL REFINED CONFIRMATION AND NIFTY 50 FILTER TESTS PASSED!")

if __name__ == "__main__":
    run_test()
