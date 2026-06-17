import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shared_data
import nse_option_chain

sys.stdout.reconfigure(encoding='utf-8')

def get_current_emulated_data():
    spot = shared_data.market_data.get("NIFTY", 0)
    if spot == 0:
        spot = 23935.85 # fallback to last known
        
    print(f"Current Spot: {spot}")
    chain = nse_option_chain.generate_emulated_option_chain("NIFTY", spot)
    if not chain or "records" not in chain or "data" not in chain["records"]:
        print("Failed to generate emulated option chain.")
        return
        
    data_list = chain["records"]["data"]
    print("=== NIFTY CURRENT EMULATED LTP & DELTA ===")
    for item in data_list:
        strike = item.get("strikePrice")
        if strike in [23900, 23950]:
            if "CE" in item:
                ce = item["CE"]
                print(f"CE {strike} | LTP: ₹{ce.get('lastPrice'):.2f} | Delta: {ce.get('delta', 0):.2f}")
            if "PE" in item:
                pe = item["PE"]
                print(f"PE {strike} | LTP: ₹{pe.get('lastPrice'):.2f} | Delta: {pe.get('delta', 0):.2f}")

if __name__ == "__main__":
    get_current_emulated_data()
