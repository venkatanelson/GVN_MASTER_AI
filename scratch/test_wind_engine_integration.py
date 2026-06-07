import sys
import os
import json

# Reconfigure stdout for utf-8 to print emojis on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Setup path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gvn_ai_wind_engine import GVNAiWindEngine

def test_integration():
    engine = GVNAiWindEngine()
    symbol = "NIFTY"
    
    print("=== SCENARIO 1: Stable Market ===")
    res1 = engine.get_market_dna(
        symbol=symbol, ltp=25000, vwap=25000,
        ce_oi=100000, pe_oi=100000, ce_coi=1000, pe_coi=1000,
        ce_vol=50000, pe_vol=50000, delta=0.5, gamma=0.015, theta=-0.5,
        ce_ltp=150.0, pe_ltp=150.0, ce_delta=0.5, pe_delta=-0.5
    )
    print(f"Wind State: {res1['wind_engine']['wind_state']}")
    print(f"Wind Power: {res1['wind_engine']['wind_power']}")
    print(f"Smart Money Status: {res1['smart_money_status']}")
    
    print("\n=== SCENARIO 2: Bullish Momentum (DPD positive for CE, negative for PE) ===")
    # Spot goes up by 20 points
    # CE expected increase = 0.5 * 20 = 10. Let's make CE go up to 165 (+15, outperforming).
    # PE expected decrease = -0.5 * 20 = -10. Let's make PE go down to 138 (-12, losing more).
    res2 = engine.get_market_dna(
        symbol=symbol, ltp=25020, vwap=25000,
        ce_oi=100000, pe_oi=120000, ce_coi=1000, pe_coi=5000,
        ce_vol=70000, pe_vol=40000, delta=0.5, gamma=0.015, theta=-0.5,
        ce_ltp=165.0, pe_ltp=138.0, ce_delta=0.5, pe_delta=-0.5
    )
    print(f"Wind State: {res2['wind_engine']['wind_state']}")
    print(f"Wind Power: {res2['wind_engine']['wind_power']}")
    print(f"Smart Money Status: {res2['smart_money_status']}")

    print("\n=== SCENARIO 3: Premium Decay Trap (Both CE & PE lose 3 points while spot is flat) ===")
    for i in range(7):
        # Tick down premiums while spot stays at 25020
        res3 = engine.get_market_dna(
            symbol=symbol, ltp=25020, vwap=25000,
            ce_oi=100000, pe_oi=100000, ce_coi=1000, pe_coi=1000,
            ce_vol=50000, pe_vol=50000, delta=0.5, gamma=0.015, theta=-0.5,
            ce_ltp=165.0 - (1.0 * (i + 1)), pe_ltp=138.0 - (1.0 * (i + 1)), ce_delta=0.5, pe_delta=-0.5
        )
    print(f"Wind State: {res3['wind_engine']['wind_state']}")
    print(f"Wind Power: {res3['wind_engine']['wind_power']}")
    print(f"Smart Money Status: {res3['smart_money_status']}")

if __name__ == "__main__":
    test_integration()
