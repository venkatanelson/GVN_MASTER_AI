import json
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Let's inspect the files in the directory to find files containing expiry information
# Or read some logs, or check `nse_option_chain.py` expiry resolution logic.
# In nse_option_chain.py:
# We resolve expiry by calling resolve_closest_future_expiry
import sqlite3

def check_recorded_expiries():
    print("=== CHECKING OPTION 915 BENCHMARKS FOR DATES AND EXPIRIES ===")
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol, timestamp FROM option_915_benchmarks ORDER BY timestamp DESC LIMIT 30")
    rows = cursor.fetchall()
    print("Distinct symbols in benchmarks:")
    for r in rows:
        print(r)
        
    # Let's see if we have option chain history
    cursor.execute("SELECT DISTINCT symbol, timestamp FROM option_chain_history ORDER BY timestamp DESC LIMIT 10")
    rows = cursor.fetchall()
    print("\nDistinct option chain history:")
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    check_recorded_expiries()
