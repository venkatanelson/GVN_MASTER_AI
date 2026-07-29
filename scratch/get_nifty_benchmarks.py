import sqlite3
import os

def main():
    db_path = "gvn_data_bank.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query Nifty benchmarks from today
    cursor.execute("""
        SELECT timestamp, strike, option_type, high, low, delta, i1, i5, i7 
        FROM option_915_benchmarks 
        WHERE symbol='NIFTY' AND date(timestamp) = '2026-07-14'
        ORDER BY timestamp ASC
    """)
    rows = cursor.fetchall()
    print("=== NIFTY 9:15 BENCHMARKS FOR 2026-07-14 ===")
    print(f"{'Time':<20} | {'Strike':<8} | {'Type':<4} | {'High':<7} | {'Low':<7} | {'Delta':<8} | {'i1':<7} | {'i5':<7} | {'i7':<7}")
    print("-" * 90)
    for r in rows:
        ts, strike, opt_type, high, low, delta, i1, i5, i7 = r
        print(f"{ts:<20} | {strike:<8} | {opt_type:<4} | {high:<7} | {low:<7} | {delta:<8.4f} | {i1:<7} | {i5:<7} | {i7:<7}")
        
    conn.close()

if __name__ == "__main__":
    main()
