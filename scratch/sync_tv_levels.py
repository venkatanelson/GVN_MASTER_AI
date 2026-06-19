import json
import sqlite3
from datetime import datetime

# 1. Update gvn_recorded_915_ohlc.json
json_path = "gvn_recorded_915_ohlc.json"
try:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    print(f"Error reading JSON: {e}")
    data = {}

# SENSEX updates
if "SENSEX" not in data:
    data["SENSEX"] = {}

data["SENSEX"]["77000 CE"] = {
    "high": 400.0,
    "low": 201.74,
    "timestamp": datetime.now().isoformat(),
    "source": "TRADINGVIEW_SYNC",
    "option_symbol": "SENSEX2661877000CE",
    "expiry_date": "2026-06-18",
    "opt_type": "CE"
}

data["SENSEX"]["77300 PE"] = {
    "high": 343.84,
    "low": 168.55,
    "timestamp": datetime.now().isoformat(),
    "source": "TRADINGVIEW_SYNC",
    "option_symbol": "SENSEX2661877300PE",
    "expiry_date": "2026-06-18",
    "opt_type": "PE"
}

# NIFTY updates
if "NIFTY" not in data:
    data["NIFTY"] = {}

data["NIFTY"]["NIFTY_SPOT"] = {
    "high": 24133.35,
    "low": 24054.93,
    "timestamp": datetime.now().isoformat(),
    "source": "TRADINGVIEW_SYNC"
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)
print("SUCCESS: Updated gvn_recorded_915_ohlc.json")


# 2. GVN Level Calculation Formula (as per nse_option_chain.py)
def calculate_gvn_levels(high915, low915, is_index=False):
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    
    if is_index:
        fib_r = diff / 0.118
        gvn0 = n2 - (0.5 * fib_r)
        gvn100 = gvn0 + fib_r
        gvnR = fib_r
        i2_ratio = 0.786
        i7_ratio = 0.236
    else:
        gvn0 = n2 * 0.118 / 0.5
        gvn100 = n1 * 0.786 / 0.5
        gvnR = gvn100 - gvn0
        i2_ratio = 0.763
        i7_ratio = 0.220
        
    return {
        "i1": round(gvn100, 2),
        "i0": round(gvn0, 2),
        "i2": round(gvn0 + i2_ratio * gvnR, 2),
        "i3": round(gvn0 + 0.618 * gvnR, 2),
        "i5": round(gvn0 + 0.500 * gvnR, 2),
        "i6": round(gvn0 + 0.382 * gvnR, 2),
        "i7": round(gvn0 + i7_ratio * gvnR, 2)
    }


# 3. Update gvn_data_bank.db
db_path = "gvn_data_bank.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # SENSEX 77000 CE
    ce_levels = calculate_gvn_levels(400.0, 201.74, is_index=False)
    cursor.execute("""
        UPDATE option_915_benchmarks
        SET high = ?, low = ?, i1 = ?, i5 = ?, i7 = ?
        WHERE symbol = 'SENSEX' AND strike = 77000 AND option_type = 'CE' AND date(timestamp) = '2026-06-18'
    """, (400.0, 201.74, ce_levels["i1"], ce_levels["i5"], ce_levels["i7"]))
    
    # SENSEX 77300 PE
    pe_levels = calculate_gvn_levels(343.84, 168.55, is_index=False)
    cursor.execute("""
        UPDATE option_915_benchmarks
        SET high = ?, low = ?, i1 = ?, i5 = ?, i7 = ?
        WHERE symbol = 'SENSEX' AND strike = 77300 AND option_type = 'PE' AND date(timestamp) = '2026-06-18'
    """, (343.84, 168.55, pe_levels["i1"], pe_levels["i5"], pe_levels["i7"]))
    
    conn.commit()
    conn.close()
    print("SUCCESS: Updated gvn_data_bank.db benchmarks")
except Exception as e:
    print(f"Error updating database: {e}")
