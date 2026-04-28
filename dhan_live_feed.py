import datetime
import time
import threading
import requests
import shared_data
import gvn_levels_engine

# DHAN LIVE FEED ENGINE v2.5
# 🌟 Cleaned and Fixed - No Null Bytes

def fetch_dhan_spot_data(symbol="NIFTY"):
    """
    Fetches the live spot price from Dhan or Backup source.
    """
    # Placeholder for actual Dhan API call
    # In live, this uses dhan.get_quote()
    try:
        # Emergency backup if Dhan API is not ready
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
    Background worker to calculate GVN levels for monitored strikes.
    """
    while True:
        try:
            # Sync Nifty Spot
            spot = fetch_dhan_spot_data("NIFTY")
            if spot > 0:
                shared_data.live_option_chain_summary["NIFTY"]["spot"] = spot
                shared_data.live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")

            # Update levels for selected strikes if missing
            # for strike in shared_data.monitored_strikes:
            #    if strike not in shared_data.strike_level_cache:
            #        levels = gvn_levels_engine.calculate_master_levels(high915, low915)
            #        shared_data.strike_level_cache[strike] = levels
            
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ [DHAN FEED ERROR] {e}")
            time.sleep(5)

def start_live_feed_worker():
    print("🚀 [Dhan Live Feed Engine] Thread Started Successfully (v2.5).")
    threading.Thread(target=process_strike_levels, daemon=True).start()

if __name__ == "__main__":
    start_live_feed_worker()
    while True: time.sleep(1)