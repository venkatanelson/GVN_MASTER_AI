import sys
import os
import json
import sqlite3

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
import shared_data
import nse_option_chain

def test_sync():
    print("=== TESTING TRADINGVIEW WEBHOOK SYNC ===")
    
    # 1. Clear JSON file to starting state
    json_path = "gvn_recorded_915_ohlc.json"
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
            print("Cleared existing JSON file.")
        except Exception as e:
            print(f"Could not clear JSON: {e}")
            
    # 2. Use flask test client
    client = app.test_client()
    
    # Test cases for different indices
    test_cases = [
        {
            "payload": {
                "secret": "ANWZ22747T",
                "symbol": "NIFTY260526C23550", # should match CE 23550
                "high": 364.75,
                "low": 320.10,
                "i1": 608.48,
                "i5": 344.65,
                "i7": 196.90
            },
            "index": "NIFTY",
            "strike": 23550.0,
            "strike_str": "23550 CE",
            "opt_type": "CE",
            "cache_key": "NIFTY_23550_CE"
        },
        {
            "payload": {
                "secret": "ANWZ22747T",
                "symbol": "BANKNIFTY260526P48000", # should match PE 48000
                "high": 450.50,
                "low": 390.20,
                "i1": 700.00,
                "i5": 410.00,
                "i7": 250.00
            },
            "index": "BANKNIFTY",
            "strike": 48000.0,
            "strike_str": "48000 PE",
            "opt_type": "PE",
            "cache_key": "BANKNIFTY_48000_PE"
        },
        {
            "payload": {
                "secret": "ANWZ22747T",
                "symbol": "SENSEX26522C80000", # SENSEX CE 80000
                "high": 120.00,
                "low": 95.00,
                "i1": 200.00,
                "i5": 110.00,
                "i7": 80.00
            },
            "index": "SENSEX",
            "strike": 80000.0,
            "strike_str": "80000 CE",
            "opt_type": "CE",
            "cache_key": "SENSEX_80000_CE"
        }
    ]
    
    for case in test_cases:
        p = case["payload"]
        print(f"\nPosting payload for {p['symbol']}...")
        response = client.post("/api/tv-levels", json=p)
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {response.get_json()}")
        assert response.status_code == 200
        
        # Check JSON file updates
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                data = json.load(f)
                
                # Assertions for index categorization in JSON
                assert case["index"] in data
                assert case["strike_str"] in data[case["index"]]
                assert data[case["index"]][case["strike_str"]]["high"] == p["high"]
                assert data[case["index"]][case["strike_str"]]["low"] == p["low"]
                print(f"Assertion Passed: JSON updated correctly for {case['index']}.")
        else:
            print("Error: JSON file was not created/updated.")
            sys.exit(1)
            
        # Check Database update
        conn = sqlite3.connect("gvn_data_bank.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, high, low, i1, i5, i7 FROM option_915_benchmarks 
            WHERE strike = ? AND option_type = ? AND symbol = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (case["strike"], case["opt_type"], case["index"]))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"Updated DB Row: Symbol={row[0]}, High={row[1]}, Low={row[2]}, i1={row[3]}, i5={row[4]}, i7={row[5]}")
            assert row[0] == case["index"]
            assert row[1] == p["high"]
            assert row[2] == p["low"]
            print(f"Assertion Passed: Database updated correctly for {case['index']}.")
        else:
            print(f"Error: Database row not found for strike {case['strike']} type {case['opt_type']}.")
            sys.exit(1)
            
        # Check Memory Cache
        ckey = case["cache_key"]
        if ckey in nse_option_chain.option_915_cache:
            val = nse_option_chain.option_915_cache[ckey]
            print(f"Updated Cache entry: {ckey} -> {val}")
            assert val == (p["high"], p["low"])
            print(f"Assertion Passed: Memory cache updated correctly for {ckey}.")
        else:
            print(f"Error: Memory cache entry not found for {ckey}.")
            sys.exit(1)

    print("\nALL TESTS PASSED SUCCESSFULLY! WEBHOOK SYNC INTEGRATION IS 100% CORRECT FOR MULTIPLE INDICES.")

if __name__ == "__main__":
    test_sync()
