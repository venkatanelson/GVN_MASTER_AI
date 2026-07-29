import sqlite3
import sys

def calculate_gvn_levels(high915, low915, is_index=False):
    if not high915 or not low915: return {}
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
        
    levels = {
        "i1": round(gvn100, 2), # GVN Top
        "i0": round(gvn0, 2),   # GVN Bottom
        "i2": round(gvn0 + i2_ratio * gvnR, 2),
        "i3": round(gvn0 + 0.618 * gvnR, 2),
        "i5": round(gvn0 + 0.500 * gvnR, 2),
        "i6": round(gvn0 + 0.382 * gvnR, 2),
        "i7": round(gvn0 + i7_ratio * gvnR, 2)
    }
    return levels

def main():
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    
    # Query all benchmarks from today
    cursor.execute("""
        SELECT symbol, strike, option_type, high, low, delta, i1, i5, i7 
        FROM option_915_benchmarks 
        WHERE date(timestamp) = '2026-07-14'
        ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()
    print("=== CHECKING ALL BENCHMARKS FOR GVN Z2H ELIGIBILITY (LOW < i7) ===")
    print(f"{'Symbol':<8} | {'Strike':<8} | {'Type':<4} | {'Low':<7} | {'i7':<7} | {'Delta':<8} | {'Qualified?':<12} | {'i0 (Bottom)':<10}")
    print("-" * 85)
    for r in rows:
        symbol, strike, opt_type, high, low, delta, i1, i5, i7 = r
        
        levels = calculate_gvn_levels(high, low, is_index=False)
        bottom_lvl = levels.get("i0", 0)
        i7_lvl = levels.get("i7", 0)
        
        abs_delta = abs(delta)
        delta_qualified = 0.40 <= abs_delta <= 0.85
        low_qualified = low < i7_lvl
        qualified = delta_qualified and low_qualified
        
        qualified_str = "YES" if qualified else "NO"
        if not delta_qualified:
            qualified_str += " (Delta)"
        elif not low_qualified:
            qualified_str += " (Low)"
            
        print(f"{symbol:<8} | {strike:<8} | {opt_type:<4} | {low:<7.2f} | {i7_lvl:<7.2f} | {delta:<8.4f} | {qualified_str:<12} | {bottom_lvl:<10.2f}")
        
    conn.close()

if __name__ == "__main__":
    main()
