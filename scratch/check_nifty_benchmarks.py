import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_nifty():
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7
        FROM option_915_benchmarks
        WHERE timestamp LIKE '2026-06-16%' AND symbol = 'NIFTY'
        ORDER BY strike ASC, option_type ASC
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} NIFTY benchmarks today:")
    for r in rows:
        strike = r[3]
        opt_type = r[4]
        high = r[5]
        low = r[6]
        delta = r[7]
        i7 = r[10]
        abs_delta = abs(delta)
        in_delta_range = 0.46 <= abs_delta <= 0.60
        low_below_i7 = low < i7 if i7 else False
        status = "QUALIFIED!" if (in_delta_range and low_below_i7) else "Failed"
        reasons = []
        if not in_delta_range: reasons.append(f"Delta {delta:.2f} out of range [0.46, 0.60]")
        if not low_below_i7: reasons.append(f"Low {low} not < i7 {i7}")
        print(f"{strike} {opt_type} | Delta: {delta:.2f} | High: {high}, Low: {low} | i7: {i7} | Status: {status} ({', '.join(reasons)})")
        
    conn.close()

if __name__ == "__main__":
    check_nifty()
