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

def login_shoonya():
    global shoonya_api
    if shoonya_api: return shoonya_api
    try:
        from NorenRestApiPy.NorenApi import NorenApi
        import pyotp
        
        db_path = 'instance/gvn_algo_pro.db' if os.path.exists('instance/gvn_algo_pro.db') else 'gvn_algo_pro.db'
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, encrypted_access_token, encrypted_password, encrypted_client_secret, encrypted_totp_key FROM user_broker_config LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            from cryptography.fernet import Fernet
            import base64
            cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
            uid = row[0]
            pwd = cipher.decrypt(row[2]).decode() if row[2] else ""
            vc = cipher.decrypt(row[1]).decode() if row[1] else uid
            app_key = cipher.decrypt(row[3]).decode() if row[3] else ""
            totp_raw = cipher.decrypt(row[4]).decode() if row[4] else ""
            
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
                        api = NorenApi(host='https://api.shoonya.com/NorenWSTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
                        api._NorenApi__userid = uid
                        api._NorenApi__susertoken = res_json.get('susertoken')
                        shoonya_api = api
                        return api
    except: pass
    return None

def fetch_data_emergency():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except: pass
    return 0

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    underlying_value = fetch_data_emergency()
    
    if underlying_value > 0:
        print(f"✅ [SYNC] NIFTY PRICE UPDATED: {underlying_value}")
        # Update SHARED DATA for the dashboard to see
        shared_data.live_option_chain_summary[symbol]["spot"] = underlying_value
        atm = int(round(underlying_value / (50 if symbol == "NIFTY" else 100)) * (50 if symbol == "NIFTY" else 100))
        shared_data.live_option_chain_summary[symbol]["atm"] = atm
        shared_data.live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
        shared_data.market_pulse[symbol]["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")

def live_feed_background_worker():
    print("🚀 [Shoonya Live Feed Engine] Thread Started Successfully.")
    while True:
        try:
            for symbol in ["NIFTY", "BANKNIFTY"]:
                analyze_and_update_gvn_scanner(symbol)
                time.sleep(2)
            time.sleep(5)
        except: time.sleep(10)

def start_live_feed_worker():
    threading.Thread(target=live_feed_background_worker, daemon=True).start()
