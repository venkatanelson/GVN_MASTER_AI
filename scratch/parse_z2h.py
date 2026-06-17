import json
import sqlite3
import sys

# Set standard output to UTF-8 to avoid charmap errors
sys.stdout.reconfigure(encoding='utf-8')

def check_live_market_data():
    print("=== LIVE MARKET DATA ===")
    try:
        with open("live_market_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        print("Keys in live_market_data:", list(data.keys()))
        if "z2h_watchlist" in data:
            print("Z2H Watchlist:")
            print(json.dumps(data["z2h_watchlist"], indent=2, ensure_ascii=False))
        else:
            # Maybe it is inside other keys? Let's check
            for k in data:
                if "watchlist" in k or "z2h" in k or "hero" in k:
                    print(f"{k}:", data[k])
    except Exception as e:
        print("Error reading live_market_data.json:", e)

def check_db_z2h():
    print("\n=== OPTION 915 BENCHMARKS FOR TODAY ===")
    try:
        conn = sqlite3.connect("gvn_data_bank.db")
        cursor = conn.cursor()
        
        # Today's benchmarks
        cursor.execute("""
            SELECT id, timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7 
            FROM option_915_benchmarks 
            WHERE timestamp LIKE '2026-06-16%'
            ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        print(f"Found {len(rows)} benchmarks for today.")
        for r in rows:
            print(f"ID: {r[0]} | TS: {r[1]} | {r[2]} {r[3]} {r[4]} | High: {r[5]}, Low: {r[6]}, Delta: {r[7]:.2f} | i1: {r[8]}, i5: {r[9]}, i7: {r[10]}")
            
        conn.close()
    except Exception as e:
        print("Error querying db:", e)

if __name__ == "__main__":
    check_live_market_data()
    check_db_z2h()
