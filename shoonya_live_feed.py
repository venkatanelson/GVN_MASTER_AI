import datetime
import math
import time
import threading
import os
import requests
import json
import httpx
import hashlib
import shared_data # Import shared memory

shoonya_master_config = {
    "client_id": None, "access_token": None, "broker_password": None, "client_secret": None,
    "totp_key": None, "broker_name": "Shoonya", "active": False
}
shoonya_api = None

def fetch_data_emergency(symbol="NIFTY"):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Mapping symbols to Yahoo Finance tickers
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

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    underlying_value = fetch_data_emergency(symbol)
    
    if underlying_value > 0:
        print(f"✅ [SYNC] {symbol} PRICE UPDATED: {underlying_value}")
        # Update SHARED DATA
        shared_data.live_option_chain_summary[symbol]["spot"] = underlying_value
        
        # Calculate ATM strike
        step = 50
        if symbol == "BANKNIFTY": step = 100
        elif symbol == "SENSEX": step = 100
        elif symbol == "FINNIFTY": step = 50
        
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
                time.sleep(1.5)
            time.sleep(3)
        except: time.sleep(10)

def start_live_feed_worker():
    threading.Thread(target=live_feed_background_worker, daemon=True).start()
