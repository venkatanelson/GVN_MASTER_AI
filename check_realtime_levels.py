import json
import os
from datetime import datetime

json_path = "live_market_data.json"

def format_status(val, level_5, level_6):
    if val >= level_5:
        return "ABOVE 0.5 [ACTIVE]"
    elif val >= level_6:
        return "BETWEEN 0.5 & 0.6 [RETEST]"
    else:
        return "BELOW 0.6 [NO MOMENTUM]"

def run_check():
    if not os.path.exists(json_path):
        print(f"[-] Market data file '{json_path}' not found. Make sure the option chain engine is running.")
        return

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[-] Error reading market data: {e}")
        return

    summary = data.get("summary", {})
    scanner = data.get("scanner", {})
    pulse = data.get("pulse", {})
    last_updated = data.get("last_updated", "UNKNOWN")

    # Get active symbols from scanner keys (e.g. NIFTY)
    symbol_keys = [k for k in scanner.keys() if k != "last_updated"]
    symbol = symbol_keys[0] if symbol_keys else "NIFTY"

    nifty_summary = summary.get(symbol, {})
    nifty_spot = nifty_summary.get("spot", 0)
    
    # Set default index GVN 0.5 level based on symbol
    if symbol == "SENSEX":
        nifty_idx_05 = 76600.00
    else:
        nifty_idx_05 = 23969.20  # Nifty GVN 0.5 Level

    print("=" * 70)
    print(f"GVN MASTER ALGO - REAL-TIME LEVEL COMPARISON REPORT")
    print(f"Last Synced: {last_updated}")
    print("=" * 70)

    # 1. Index Section
    idx_status = "BELOW 0.5 [BEARISH]" if nifty_spot < nifty_idx_05 else "ABOVE 0.5 [BULLISH]"
    print(f"Index Spot ({symbol}): {nifty_spot:.2f} | GVN 0.5 Level: {nifty_idx_05:.2f} | Status: {idx_status}")
    print("-" * 70)

    # 2. Options Section
    nifty_scanner = scanner.get(symbol, [])
    ce_item = None
    pe_item = None

    # Find the nearest active CE/PE from scanner list
    for item in nifty_scanner:
        strike_name = item.get("strike", "")
        if "CE" in strike_name and not ce_item:
            ce_item = item
        elif "PE" in strike_name and not pe_item:
            pe_item = item

    # If not in scanner, try to find specific strikes
    if not ce_item or not pe_item:
        for item in nifty_scanner:
            strike_name = item.get("strike", "")
            if "CE" in strike_name:
                ce_item = item
            if "PE" in strike_name:
                pe_item = item

    if ce_item:
        ce_strike = ce_item.get("strike")
        ce_ltp = ce_item.get("ltp", 0)
        ce_levels = ce_item.get("levels", {})
        ce_05 = float(ce_levels.get("i5", 0))
        ce_06 = float(ce_levels.get("i6", 0))
        ce_status = format_status(ce_ltp, ce_05, ce_06)
        ce_wind = ce_item.get("wind", "UNKNOWN")
        print(f"CALL Option: {ce_strike} | LTP: {ce_ltp:.2f}")
        print(f"  Levels   : 0.5 (i5): {ce_05:.2f} | 0.6 (i6): {ce_06:.2f}")
        print(f"  Status   : {ce_status} | Wind: {ce_wind}")
    else:
        print("CALL Option: No Call Option found in active scanner list.")

    print("-" * 70)

    if pe_item:
        pe_strike = pe_item.get("strike")
        pe_ltp = pe_item.get("ltp", 0)
        pe_levels = pe_item.get("levels", {})
        pe_05 = float(pe_levels.get("i5", 0))
        pe_06 = float(pe_levels.get("i6", 0))
        pe_status = format_status(pe_ltp, pe_05, pe_06)
        pe_wind = pe_item.get("wind", "UNKNOWN")
        print(f"PUT Option : {pe_strike} | LTP: {pe_ltp:.2f}")
        print(f"  Levels   : 0.5 (i5): {pe_05:.2f} | 0.6 (i6): {pe_06:.2f}")
        print(f"  Status   : {pe_status} | Wind: {pe_wind}")
    else:
        print("PUT Option : No Put Option found in active scanner list.")

    print("=" * 70)

    # 3. GVN Dual-Sync Breakout Logic Alert
    print("GVN DUAL-SYNC BREAKOUT ALERT:")
    if nifty_spot < nifty_idx_05:
        # Bearish setup
        if pe_item and pe_ltp >= pe_05:
            print("   [+] PUT BREAKOUT CONFIRMED! Index is below 0.5 AND Put is above 0.5.")
            print("       Action: Strong PE Buy Momentum (2x Volume Entry). Target: i3.")
        elif pe_item and pe_ltp >= pe_06:
            print("   [*] PUT RETRACEMENT VALID: Index is below 0.5 AND Put is holding above 0.6.")
            print("       Action: Buy PE on Pullback near i6/i7 support.")
        else:
            print("   [!] DIVERGENCE DETECTED: Index is down, but Put Option has no strength (below 0.6).")
            print("       Action: NO TRADE (Avoid false breakouts).")
    else:
        # Bullish setup
        if ce_item and ce_ltp >= ce_05:
            print("   [+] CALL BREAKOUT CONFIRMED! Index is above 0.5 AND Call is above 0.5.")
            print("       Action: Strong CE Buy Momentum (2x Volume Entry). Target: i3.")
        elif ce_item and ce_ltp >= ce_06:
            print("   [*] CALL RETRACEMENT VALID: Index is above 0.5 AND Call is holding above 0.6.")
            print("       Action: Buy CE on Pullback near i6/i7 support.")
        else:
            print("   [!] DIVERGENCE DETECTED: Index is up, but Call Option has no strength (below 0.6).")
            print("       Action: NO TRADE (Avoid false breakouts).")
    print("=" * 70)

if __name__ == "__main__":
    run_check()
