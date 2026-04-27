import datetime
import math
import time
import threading
import os
import requests
import json
import httpx
import hashlib
import shared_data 
import gvn_alpha_engine # 🚀 Our new Master Logic Engine

shoonya_master_config = {
    "client_id": None, "access_token": None, "broker_password": None, "client_secret": None,
    "totp_key": None, "broker_name": "Shoonya", "active": False
}
shoonya_api = None

def fetch_data_emergency(symbol="NIFTY"):
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
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except: pass
    return 0

def monitor_selected_strikes():
    """
    Background logic to process i-levels for strikes selected by the user in the UI.
    """
    for strike_type in ['CALL', 'PUT']:
        strike = shared_data.monitored_strikes[strike_type]
        symbol = strike['symbol']
        
        if symbol:
            # 1. Check if levels are already calculated for today
            if symbol not in shared_data.i_level_memory:
                print(f"📊 [ALPHA ENGINE] Calculating i-Levels for {symbol}...")
                # For now, if we don't have broker API, we use a mock 9:15 data
                # In production, this would use shoonya_api.get_historical_data
                mock_high = 100 # Default fallback
                mock_low = 90
                mock_close = 95
                
                levels = gvn_alpha_engine.calculate_gvn_levels(mock_high, mock_low, mock_close)
                shared_data.i_level_memory[symbol] = levels
                shared_data.monitored_strikes[strike_type]['levels'] = levels
            
            # 2. Update current price and check momentum
            # (In production, fetch live price for the specific strike)
            # strike['last_price'] = ...
            pass

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    underlying_value = fetch_data_emergency(symbol)
    
    if underlying_value > 0:
        # Update SHARED DATA
        shared_data.live_option_chain_summary[symbol]["spot"] = underlying_value
        
        step = 50
        if symbol == "BANKNIFTY": step = 100
        elif symbol == "SENSEX": step = 100
        
        atm = int(round(underlying_value / step) * step)
        shared_data.live_option_chain_summary[symbol]["atm"] = atm
        shared_data.live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")

def live_feed_background_worker():
    print("🚀 [Shoonya Live Feed Engine] Thread Started Successfully.")
    while True:
        try:
            # Sync for all major indices
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]:
                analyze_and_update_gvn_scanner(symbol)
                time.sleep(1)
            
            # Monitor user-selected strikes
            monitor_selected_strikes()
            
            time.sleep(2)
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(5)

def start_live_feed_worker():
    threading.Thread(target=live_feed_background_worker, daemon=True).start()
