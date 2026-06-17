import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

def calculate_levels(high, low):
    diff = high - low
    result = diff / 2
    n1 = high + result
    n2 = low + result
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    return {
        "i1_top": round(gvn100, 2),
        "i0_bottom": round(gvn0, 2),
        "i2": round(gvn0 + 0.763 * gvnR, 2),
        "i3": round(gvn0 + 0.618 * gvnR, 2),
        "i5": round(gvn0 + 0.500 * gvnR, 2),
        "i6": round(gvn0 + 0.382 * gvnR, 2),
        "i7": round(gvn0 + 0.220 * gvnR, 2)
    }

def print_locked_strikes():
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    
    # We query NIFTY 23900 CE and NIFTY 23950 PE
    cursor.execute("""
        SELECT symbol, strike, option_type, high, low, delta, i1, i5, i7
        FROM option_915_benchmarks
        WHERE timestamp LIKE '2026-06-16%' AND symbol = 'NIFTY' AND strike IN (23900, 23950)
    """)
    rows = cursor.fetchall()
    print("=== NIFTY MASTER STRKE LEVELS FOR TODAY ===")
    for r in rows:
        sym, strike, opt_type, high, low, delta, db_i1, db_i5, db_i7 = r
        levels = calculate_levels(high, low)
        
        # Get latest LTP from option_chain_history
        cursor.execute("""
            SELECT ltp, timestamp FROM option_chain_history
            WHERE symbol = 'NIFTY' AND strike_price = ? AND option_type = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (strike, opt_type))
        ltp_row = cursor.fetchone()
        ltp = ltp_row[0] if ltp_row else "N/A"
        ltp_time = ltp_row[1] if ltp_row else "N/A"
        
        print(f"\n🎯 {sym} {int(strike)} {opt_type} (Delta: {delta:.2f})")
        print(f"  • 9:15 AM Candle: High = ₹{high:.2f}, Low = ₹{low:.2f}")
        print(f"  • Latest LTP    : ₹{ltp} (at {ltp_time})")
        print(f"  • GVN Levels (nse_option_chain.py mapping):")
        print(f"    - GVN Top (i1)      : ₹{levels['i1_top']:.2f}")
        print(f"    - GVN Bottom (i0)   : ₹{levels['i0_bottom']:.2f} (Z2H Entry Zone)")
        print(f"    - Level i7          : ₹{levels['i7']:.2f} (Second Entry / Retracement)")
        print(f"    - Level i6          : ₹{levels['i6']:.2f}")
        print(f"    - Level i5 (Blue)   : ₹{levels['i5']:.2f} (Morning Momentum)")
        print(f"    - Level i3          : ₹{levels['i3']:.2f}")
        print(f"    - Level i2          : ₹{levels['i2']:.2f}")
        
    conn.close()

if __name__ == "__main__":
    print_locked_strikes()
