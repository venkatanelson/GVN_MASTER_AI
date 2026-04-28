import datetime
import time
import threading
import requests
import shared_data
import gvn_levels_engine

# DHAN LIVE FEED ENGINE v2.5
# 🌟 Dynamic 14-Strike Level Engine Integrated

def fetch_dhan_spot_data(symbol="NIFTY"):
    """
    Fetches the live spot price from Dhan or Backup source.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        ticker = "%5ENSEI" if symbol == "NIFTY" else "%5ENSEBANK"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return float(data['chart']['result'][0]['meta']['regularMarketPrice'])
    except:
        pass
    return 0

def process_strike_levels():
    """
    Background worker to calculate GVN levels for 14 active strikes around ATM.
    """
    print("🛰️ [GVN SCANNER] Initializing 14-Strike Dynamic Monitor...")
    while True:
        try:
            # 1. Sync Nifty Spot
            spot = fetch_dhan_spot_data("NIFTY")
            if spot > 0:
                shared_data.live_option_chain_summary["NIFTY"]["spot"] = spot
                shared_data.live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")

                # 2. Identify 14 Strikes around ATM (Step 50 for Nifty)
                atm = int(round(spot / 50) * 50)
                strikes_to_scan = []
                for i in range(-3, 4): # -150 to +150 range
                    strike_price = atm + (i * 50)
                    strikes_to_scan.append(f"NIFTY{strike_price}CE")
                    strikes_to_scan.append(f"NIFTY{strike_price}PE")

                # 3. Calculate Levels for each strike
                for symbol in strikes_to_scan:
                    if symbol not in shared_data.strike_level_cache:
                        # Simulation of 9:15 High/Low extraction
                        # In production, this pulls from dhan.get_historical_data
                        mock_h = 100.0 
                        mock_l = 50.0
                        
                        levels = gvn_levels_engine.calculate_master_levels(mock_h, mock_l)
                        if levels:
                            shared_data.strike_level_cache[symbol] = levels
                            # Also update monitored strikes for UI
                            st_type = "CALL" if "CE" in symbol else "PUT"
                            # shared_data.monitored_strikes[st_type] = {"symbol": symbol, "levels": levels}
                
            time.sleep(10) # Refresh ATM/Strikes every 10 seconds
        except Exception as e:
            print(f"⚠️ [DHAN FEED ERROR] {e}")
            time.sleep(5)

def start_live_feed_worker():
    print("🚀 [Dhan Live Feed Engine] Thread Started Successfully (v2.5).")
    threading.Thread(target=process_strike_levels, daemon=True).start()

if __name__ == "__main__":
    start_live_feed_worker()
    while True: time.sleep(1)