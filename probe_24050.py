
import shared_data
import json
import gvn_levels_engine

def get_24050_levels():
    print("--- GVN LEVEL 7 CHECK FOR 24050 ---")
    
    # Check if 24050 is in the current alpha grid
    target_strike = 24050
    found = False
    
    # Scan shared_data scanner data
    scanner = shared_data.gvn_scanner_data.get("scanner", {}).get("NIFTY", [])
    for item in scanner:
        if str(target_strike) in item["strike"]:
            found = True
            print(f"Found Strike: {item['strike']}")
            print(f"LTP: {item['ltp']}")
            print(f"i-Levels: {json.dumps(item['levels'], indent=2)}")
            print(f"AI Signal: {item['ai_signal']}")
            print(f"Market Score: {item['score']}")
    
    if not found:
        print(f"Strike {target_strike} not found in current Alpha Grid.")
        print("Please provide 9:15 AM High and Low for manual calculation.")

if __name__ == "__main__":
    get_24050_levels()
