import datetime
import time
import threading
import requests
import shared_data
import gvn_levels_engine

# DHAN LIVE FEED ENGINE v2.5
# 🌟 Cleaned and Fixed - No Null Bytes

dhan_master_config = {
    "client_id": None, "access_token": None, "broker_name": "Dhan", "active": False
}

shoonya_master_config = {
    "client_id": None, "password": None, "totp_key": None, "broker_name": "Shoonya", "active": False
}

def fetch_dhan_spot_data(symbol="NIFTY"):
    """
    Fetches the live spot price from Dhan or Backup source.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        tickers = {
            "NIFTY": "%5ENSEI",
            "BANKNIFTY": "%5ENSEBANK",
            "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
            "SENSEX": "%5EBSESN"
        }
        ticker = tickers.get(symbol, "%5ENSEI")
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
    Background worker to calculate GVN levels for active strikes around ATM.
    Populates shared_data.gvn_scanner_data for the Dashboard.
    """
    print("🛰️ [GVN SCANNER] Initializing Dynamic Multi-Index Monitor...")
    while True:
        try:
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]:
                # 1. Sync Spot Price
                spot = fetch_dhan_spot_data(symbol)
                if spot > 0:
                    shared_data.live_option_chain_summary[symbol]["spot"] = spot
                    shared_data.live_option_chain_summary[symbol]["atm"] = int(round(spot / 50) * 50) if symbol == "NIFTY" else int(round(spot / 100) * 100)
                    shared_data.live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")

                    # 2. Identify Strikes around ATM
                    step = 50 if symbol == "NIFTY" else 100
                    atm = int(round(spot / step) * step)
                    
                    scanner_list = []
                    # Scan 2 strikes ITM and 2 strikes OTM for each side
                    for i in range(-2, 3):
                        strike_price = atm + (i * step)
                        for opt_type in ["CE", "PE"]:
                            strike_symbol = f"{symbol} {strike_price} {opt_type}"
                            
                            # 3. Calculate Levels (Using Mock High/Low for now, replace with 9:15 data later)
                            mock_h = strike_price * 0.01 + 50 # Example mock
                            mock_l = strike_price * 0.01
                            levels = gvn_levels_engine.calculate_master_levels(mock_h, mock_l)
                            
                            # Determine basic signal for UI
                            ltp = mock_l + 10 # Mock LTP
                            ai_signal = "WAIT"
                            if levels:
                                if ltp > levels['i5']: ai_signal = "🚀 BUY"
                                elif ltp < levels['i7']: ai_signal = "📉 SELL"
                            
                            scanner_list.append({
                                "strike": strike_symbol,
                                "ltp": round(ltp, 2),
                                "delta": 0.50, # Mock
                                "zone": "ALPHA ZONE",
                                "ai_signal": ai_signal,
                                "score": 75,
                                "levels": levels
                            })
                    
                    shared_data.gvn_scanner_data[symbol] = scanner_list
            
            shared_data.gvn_scanner_data["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
            time.sleep(5) # Refresh every 5 seconds
        except Exception as e:
            print(f"⚠️ [DHAN FEED ERROR] {e}")
            time.sleep(5)

def start_live_feed_worker():
    print("🚀 [Dhan Live Feed Engine] Thread Started Successfully (v2.5).")
    threading.Thread(target=process_strike_levels, daemon=True).start()

if __name__ == "__main__":
    start_live_feed_worker()
    while True: time.sleep(1)