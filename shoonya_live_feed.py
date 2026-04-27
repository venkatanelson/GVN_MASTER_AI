import datetime
import math
import time
import threading
import os
import requests
import json
import httpx
import hashlib

# Global memory for Shoonya Live Feed Engine
current_delta_60_strikes = {
    "NIFTY": {"CE": None, "PE": None, "expiry": None},
    "BANKNIFTY": {"CE": None, "PE": None, "expiry": None},
    "FINNIFTY": {"CE": None, "PE": None, "expiry": None},
    "SENSEX": {"CE": None, "PE": None, "expiry": None},
    "last_updated": None
}

gvn_scanner_data = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
    "SENSEX": [],
    "last_updated": None
}

live_option_chain_summary = {
    "NIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "BANKNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "FINNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "SENSEX": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "last_updated": None
}

full_option_chain_data = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
    "last_updated": None
}

market_pulse = {
    "NIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "BANKNIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "last_updated": None
}

live_option_ltps = {}
option_ltp_history = {} 
option_915_candles = {} 
auto_trade_signals = [] # Added missing signals list

shoonya_master_config = {
    "client_id": None, "access_token": None, "broker_password": None, "client_secret": None,
    "totp_key": None, "broker_name": "Shoonya", "active": False
}
shoonya_api = None

def login_shoonya():
    global shoonya_api
    if shoonya_api: return shoonya_api
    try:
        from NorenRestApiPy.NorenApi import NorenApi
        import pyotp
        
        api = NorenApi(host='https://api.shoonya.com/NorenWSTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        
        uid = shoonya_master_config.get("client_id")
        pwd = shoonya_master_config.get("broker_password")
        vc = shoonya_master_config.get("access_token") or uid
        app_key = shoonya_master_config.get("client_secret")
        totp_raw = shoonya_master_config.get("totp_key")
        
        token = pyotp.TOTP(totp_raw).now() if totp_raw else ""

        url = "https://api.shoonya.com/NorenWSTP/QuickAuthenticate"
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        appkey_hash = hashlib.sha256(f"{uid}|{app_key}".encode()).hexdigest()
        
        payload = {
            "apkversion": "js:1.0.0", "uid": uid, "pwd": pwd_hash,
            "factor2": token, "vc": vc, "appkey": appkey_hash,
            "imei": "ABC123456789", "source": "API"
        }
        
        with httpx.Client(http2=True) as client:
            resp = client.post(url, data={"jData": json.dumps(payload)})
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get('stat') == 'Ok':
                    api._NorenApi__userid = uid
                    api._NorenApi__password = pwd
                    api._NorenApi__susertoken = res_json.get('susertoken')
                    shoonya_api = api
                    return api
        return None
    except: return None

def fetch_data_emergency():
    try:
        # Reliable public source for Nifty 50
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except: pass
    return 0

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    api = login_shoonya()
    underlying_value = 0
    
    if api:
        try:
            tokens = {"NIFTY": "26000", "BANKNIFTY": "26009"}
            quote = api.get_quotes("NSE", tokens.get(symbol, "26000"))
            if quote and quote.get('stat') == 'Ok':
                underlying_value = float(quote.get('lp', 0))
        except: pass
    
    if underlying_value == 0:
        underlying_value = fetch_data_emergency()

    if underlying_value > 0:
        # Update both the specific symbol and the general summary for the UI
        live_option_chain_summary[symbol]["spot"] = underlying_value
        atm = int(round(underlying_value / (50 if symbol == "NIFTY" else 100)) * (50 if symbol == "NIFTY" else 100))
        live_option_chain_summary[symbol]["atm"] = atm
        live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
        market_pulse[symbol]["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")

def live_feed_background_worker():
    print("🚀 [Shoonya Live Feed Engine] Thread Started Successfully.")
    while True:
        try:
            db_path = 'instance/gvn_algo_pro.db' if os.path.exists('instance/gvn_algo_pro.db') else 'gvn_algo_pro.db'
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT client_id, encrypted_access_token, encrypted_password, encrypted_client_secret, encrypted_totp_key, broker_name FROM user_broker_config LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                from cryptography.fernet import Fernet
                import base64
                cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
                shoonya_master_config.update({
                    "client_id": row[0],
                    "access_token": cipher.decrypt(row[1]).decode() if row[1] else "",
                    "broker_password": cipher.decrypt(row[2]).decode() if row[2] else "",
                    "client_secret": cipher.decrypt(row[3]).decode() if row[3] else "",
                    "totp_key": cipher.decrypt(row[4]).decode() if row[4] else "",
                    "broker_name": row[5] or "Shoonya",
                    "active": True
                })

            for symbol in ["NIFTY", "BANKNIFTY"]:
                analyze_and_update_gvn_scanner(symbol)
                time.sleep(2)
            time.sleep(5)
        except Exception as e:
            time.sleep(10)

def start_live_feed_worker():
    threading.Thread(target=live_feed_background_worker, daemon=True).start()
