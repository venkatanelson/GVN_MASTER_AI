"""
GVN Wind Integration Verification Script
Verifies S&R breakout/wall-bounce dampening and FII flow scaling inside GVNAiWindEngine.
"""

import sys
import os
import sqlite3

# Add workspace path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gvn_data_bank import save_fii_dii_record, get_latest_fii_dii, init_db
from gvn_ai_wind_engine import GVNAiWindEngine

def run_test():
    print("[START] Running Wind S&R and FII/DII Integration Verification Tests")
    print("-" * 65)
    
    init_db()
    
    # Back up original FII/DII
    original_latest = get_latest_fii_dii()
    if original_latest:
        print(f"Backed up original latest FII/DII: Date={original_latest['date']}, Cash={original_latest['fii_cash']}")
    
    # Base setup:
    # A bullish scenario: price is above VWAP (25000), CE COI is unwinding (-20k)
    # This naturally produces a "SHORT COVERING" or "UP WIND" bullish wind state.
    def get_bullish_test_args(ltp, support, resistance):
        return {
            "symbol": "NIFTY", "ltp": ltp, "vwap": 24900,
            "ce_oi": 100000, "pe_oi": 100000,
            "ce_coi": -20000, "pe_coi": 10000,
            "ce_vol": 100000, "pe_vol": 100000,
            "delta": 0.60, "gamma": 0.015, "theta": -0.5,
            "support_strike": support, "resistance_strike": resistance
        }

    # A bearish scenario: price is below VWAP, PE COI is unwinding (-20k)
    # This naturally produces a "LONG UNWINDING" or "DOWN WIND" bearish wind state.
    def get_bearish_test_args(ltp, support, resistance):
        return {
            "symbol": "NIFTY", "ltp": ltp, "vwap": 25100,
            "ce_oi": 100000, "pe_oi": 100000,
            "ce_coi": 10000, "pe_coi": -20000,
            "ce_vol": 100000, "pe_vol": 100000,
            "delta": -0.60, "gamma": 0.015, "theta": -0.5,
            "support_strike": support, "resistance_strike": resistance
        }

    all_passed = True
    
    # Test Cases
    # Format: (Name, Spot, Support, Resistance, Mock FII Cash, Type, Expected FII Mult, Expected SR Mult, Expected SR Status)
    test_cases = [
        (
            "Test 1: Stable Zone (No FII / No S&R proximity)",
            25000, 24500, 25500, 0.0, "BULLISH",
            1.0, 1.0, "STABLE"
        ),
        (
            "Test 2: Approaching Resistance (Ceiling - Damps Bullish Wind)",
            25075, 24500, 25100, 0.0, "BULLISH", # Approach within 45pts (25100 - 25075 = 25)
            1.0, 0.70, "APPROACHING RESISTANCE"
        ),
        (
            "Test 3: Resistance Broken (Breakout - Boosts Bullish Wind)",
            25120, 24500, 25100, 0.0, "BULLISH", # Spot broke above 25100
            1.0, 1.30, "RESISTANCE BROKEN"
        ),
        (
            "Test 4: Heavy FII Selling on Bullish Wind (Headwind - Damps)",
            25000, 24500, 25500, -2500.0, "BULLISH",
            0.70, 1.0, "STABLE"
        ),
        (
            "Test 5: Heavy FII Selling on Bearish Wind (Tailwind - Boosts)",
            25000, 24500, 25500, -2500.0, "BEARISH",
            1.25, 1.0, "STABLE"
        ),
        (
            "Test 6: Heavy FII Buying on Bullish Wind (Tailwind - Boosts)",
            25000, 24500, 25500, 2000.0, "BULLISH",
            1.25, 1.0, "STABLE"
        ),
        (
            "Test 7: Approaching Support (Floor - Damps Bearish Wind)",
            24925, 24900, 25500, 0.0, "BEARISH", # Approach within 45pts (24925 - 24900 = 25)
            1.0, 0.70, "APPROACHING SUPPORT"
        ),
        (
            "Test 8: Support Broken (Panic Fall - Boosts Bearish Wind)",
            24880, 24900, 25500, 0.0, "BEARISH", # Spot broke below 24900
            1.0, 1.30, "SUPPORT BROKEN"
        )
    ]

    for name, spot, support, resistance, fii, direction, exp_fii_m, exp_sr_m, exp_sr_status in test_cases:
        print(f"\n[CASE] {name}")
        
        # Fresh wind engine instance to prevent history pollution
        engine = GVNAiWindEngine()
        
        # Save mock FII EOD cash flow
        save_fii_dii_record("9999-12-31", fii, 0.0, 0.0, 0.0, 0.0)
        
        # Setup engine arguments and establish price memory trend direction (3 ticks total)
        if direction == "BULLISH":
            # Tick 1 (spot - 20), Tick 2 (spot - 10), Tick 3 (spot)
            prev_args1 = get_bullish_test_args(spot - 20, support, resistance)
            engine.get_market_dna(**prev_args1)
            prev_args2 = get_bullish_test_args(spot - 10, support, resistance)
            engine.get_market_dna(**prev_args2)
            args = get_bullish_test_args(spot, support, resistance)
        else:
            # Tick 1 (spot + 20), Tick 2 (spot + 10), Tick 3 (spot)
            prev_args1 = get_bearish_test_args(spot + 20, support, resistance)
            engine.get_market_dna(**prev_args1)
            prev_args2 = get_bearish_test_args(spot + 10, support, resistance)
            engine.get_market_dna(**prev_args2)
            args = get_bearish_test_args(spot, support, resistance)
            
        res = engine.get_market_dna(**args)
        wind = res["wind_engine"]
        metrics = wind["metrics"]
        
        actual_fii_m = metrics["fii_multiplier"]
        actual_sr_m = metrics["sr_multiplier"]
        actual_sr_status = metrics["sr_status"]
        
        safe_state = wind['wind_state'].encode('ascii', errors='ignore').decode('ascii')
        safe_sr_status = actual_sr_status.encode('ascii', errors='ignore').decode('ascii')
        
        print(f"  Wind State : {safe_state}")
        print(f"  FII Cash   : {metrics['fii_cash']} -> Mult: {actual_fii_m} (Expected: {exp_fii_m})")
        print(f"  S&R Status : {safe_sr_status} (Expected: {exp_sr_status}) -> Mult: {actual_sr_m} (Expected: {exp_sr_m})")
        
        # Assertions
        fii_ok = abs(actual_fii_m - exp_fii_m) < 0.01
        sr_ok = abs(actual_sr_m - exp_sr_m) < 0.01
        status_ok = actual_sr_status == exp_sr_status
        
        if fii_ok and sr_ok and status_ok:
            print("  [PASS] Test case passed.")
        else:
            print(f"  [FAIL] FII match: {fii_ok}, S&R match: {sr_ok}, Status match: {status_ok}")
            all_passed = False
            
    # Clean up mock records
    try:
        conn = sqlite3.connect("gvn_data_bank.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fii_dii_history WHERE date = '9999-12-31'")
        conn.commit()
        conn.close()
        print("\n[CLEANUP] Deleted mock test record.")
    except Exception as e:
        print(f"\n[WARNING] Cleanup failed: {e}")
        
    if original_latest:
        save_fii_dii_record(
            date_str=original_latest["date"],
            fii_cash=original_latest["fii_cash"],
            dii_cash=original_latest["dii_cash"],
            fii_idx_fut=original_latest["fii_idx_fut"],
            fii_idx_opt=original_latest["fii_idx_opt"],
            fii_stk_fut=original_latest["fii_stk_fut"]
        )
        print("[CLEANUP] Restored original latest FII/DII record.")
        
    print("-" * 65)
    if all_passed:
        print("[RESULT] ALL WIND DIRECTION VERIFICATION TESTS PASSED!")
    else:
        print("[RESULT] SOME VERIFICATION TESTS FAILED. CHECK LOGS.")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
