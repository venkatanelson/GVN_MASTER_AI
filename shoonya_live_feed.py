import datetime
import math
import time
import threading
import os
import requests

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

def calculate_option_gvn_levels(high915, low915):
    if not high915 or not low915: return {}
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    levels = {
        "i0": gvn100, "i1": gvn0, "i2": gvn0 + 0.763 * gvnR,
        "i3": gvn0 + 0.618 * gvnR, "i5": gvn0 + 0.5 * gvnR,
        "i6": gvn0 + 0.382 * gvnR, "i7": gvn0 + 0.220 * gvnR
    }
    return levels

def update_ai_dashboard(symbol, underlying_value):
    try:
        scanner_list = gvn_scanner_data.get(symbol, [])
        if not scanner_list: return
        
        status_labels = []
        sentiment, trend, color_code, score = "NATURAL 📊", "SIDEWAYS", "yellow", 50
        
        ce_vol = sum(item.get('volume', 0) for item in scanner_list if 'CE' in item.get('strike_name', ''))
        pe_vol = sum(item.get('volume', 0) for item in scanner_list if 'PE' in item.get('strike_name', ''))
        vol_ratio = pe_vol / (ce_vol if ce_vol > 0 else 1)
        
        if vol_ratio > 1.8:
            sentiment, trend, color_code, score = "STRONG BUY 🚀", "ULTRA BREAKOUT", "rainbow", 95
            status_labels.append("HIGH MOMENTUM 🔥")
        elif vol_ratio > 1.3:
            sentiment, trend, color_code, score = "BUY 📈", "UPTREND", "green", 75
        elif vol_ratio < 0.4:
            sentiment, trend, color_code, score = "STRONG SELL 🩸", "ULTRA CRASH", "rainbow", 5
        elif vol_ratio < 0.7:
            sentiment, trend, color_code, score = "SELL 📉", "DOWNTREND", "red", 25

        market_pulse[symbol] = {
            "sentiment": sentiment, "score": score, "trend": trend,
            "volume": "HIGH" if len(status_labels) > 3 else "NORMAL",
            "inst_activity": "ACTIVE 🔥" if any(item.get('score', 0) > 65 for item in scanner_list) else "LOW",
            "color": color_code, "labels": status_labels[:6], "last_updated": datetime.datetime.now().strftime("%H:%M:%S")
        }
    except: pass

def calculate_gvn_levels(high915, low915):
    if not high915 or not low915: return {}
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    return {
        "Level_0": gvn100, "Level_1": gvn0, "Level_2": gvn0 + 0.763 * gvnR,
        "Level_3": gvn0 + 0.618 * gvnR, "Level_5": gvn0 + 0.500 * gvnR,
        "Level_6": gvn0 + 0.382 * gvnR, "Level_7": gvn0 + 0.220 * gvnR
    }

def norm_pdf(x): return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
def norm_cdf(x): return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def calculate_greeks(S, K, T, r, sigma, option_type):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0: return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        delta = norm_cdf(d1) if option_type == "CE" else norm_cdf(d1) - 1.0
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        return {"delta": round(delta, 3), "gamma": round(gamma, 4), "theta": 0.0, "vega": 0.0}
    except: return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

auto_trade_signals = []
def generate_deep_scan_signal(symbol, item, greeks, spot, oi, oi_change):
    global auto_trade_signals
    delta = abs(greeks.get("delta", 0))
    if 0.30 <= delta <= 0.60 and oi_change > 0:
        signal = {"symbol": symbol, "strike": item.get("strike"), "ltp": item.get("ltp"), "delta": delta, "time": datetime.datetime.now().strftime("%H:%M:%S")}
        auto_trade_signals.insert(0, signal)
        if len(auto_trade_signals) > 20: auto_trade_signals = auto_trade_signals[:20]

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
        class ShoonyaApiPy(NorenApi):
            def __init__(self):
                NorenApi.__init__(self, host='https://api.shoonya.com/NorenWSTP/', websocket='wss://api.shoonya.com/NorenWSTP/', eodhost='https://api.shoonya.com/chartApi/getdata/')
        api = ShoonyaApiPy()
        uid, pwd = shoonya_master_config.get("client_id"), shoonya_master_config.get("broker_password")
        factor2 = pyotp.TOTP(shoonya_master_config.get("totp_key", "")).now() if shoonya_master_config.get("totp_key") else ""
        vc, app_key = shoonya_master_config.get("access_token"), shoonya_master_config.get("client_secret")
        if not uid or not pwd: return None
        ret = api.login(userid=uid, password=pwd, twoFA=factor2, vendor_code=vc, api_secret=app_key, imei='12345')
        if ret and ret.get('stat') == 'Ok':
            shoonya_api = api
            with open("shoonya_feed_status.log", "a") as f: f.write(f"{datetime.datetime.now()}: [SHOONYA API] Login Successful.\n")
            return api
    except Exception as e:
        with open("shoonya_feed_status.log", "a") as f: f.write(f"{datetime.datetime.now()}: [SHOONYA API] Login Failed: {e}\n")
    return None

def fetch_option_chain(symbol="NIFTY"):
    broker = shoonya_master_config.get("broker_name", "Shoonya")
    
    if broker == "Shoonya":
        api = login_shoonya()
        if not api: return None
        try:
            tokens = {"NIFTY": "26000", "BANKNIFTY": "26009", "FINNIFTY": "26037", "SENSEX": "1"}
            quote = api.get_quotes("NSE", tokens.get(symbol, "26000"))
            lp = float(quote.get('lp', 0))
            
            # 🛑 NO NSE SCRAPING - ONLY BROKER API 🛑
            # Since Shoonya native option chain is multi-step, we use a placeholder or return LTP for now.
            # Real Shoonya Option Chain requires searching symbols and getting quotes for each.
            return {"records": {"underlyingValue": lp, "expiryDates": [], "data": []}, "source": "SHOONYA_API_ONLY"}
        except: return None

    if broker == "Dhan" and shoonya_master_config.get("active"):
        from dhanhq import dhanhq
        try:
            dhan = dhanhq(shoonya_master_config["client_id"], shoonya_master_config["access_token"])
            sec_ids = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27", "SENSEX": "1"}
            sid = sec_ids.get(symbol)
            lp_resp = dhan.quote_data({"IDX_I": [sid]})
            lp = lp_resp.get('data', {}).get(sid, {}).get('lastPrice', 0)
            
            expiry_resp = dhan.expiry_list(sid, "IDX_I")
            if expiry_resp.get('status') == 'success' and expiry_resp.get('data'):
                expiry = expiry_resp.get('data')[0]
                chain_resp = dhan.option_chain(sid, "IDX_I", expiry)
                if chain_resp.get('status') == 'success':
                    return {"records": {"underlyingValue": lp, "expiryDates": [expiry], "data": chain_resp.get('data', [])}, "source": "DHAN_API_ONLY"}
        except: pass
    return None

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    data = fetch_option_chain(symbol)
    if not data or "records" not in data: return
    
    records = data["records"]
    underlying_value = records.get("underlyingValue", 0)
    gvn_scanner_data[symbol] = []
    
    if underlying_value > 0:
        live_option_chain_summary[symbol]["spot"] = underlying_value
        atm = int(round(underlying_value / (50 if symbol == "NIFTY" else 100)) * (50 if symbol == "NIFTY" else 100))
        live_option_chain_summary[symbol]["atm"] = atm
        live_option_chain_summary["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
        update_ai_dashboard(symbol, underlying_value)

def live_feed_background_worker():
    print("🚀 [Shoonya Live Feed Engine] Thread Started Successfully.")
    while True:
        try:
            if not shoonya_master_config.get('active'):
                db_url = os.environ.get('DATABASE_URL')
                row = None
                if db_url:
                    import psycopg2
                    conn = psycopg2.connect(db_url.replace("postgres://", "postgresql://", 1))
                    cursor = conn.cursor()
                    cursor.execute("SELECT client_id, encrypted_access_token, encrypted_password, encrypted_client_secret, encrypted_totp_key, broker_name FROM user_broker_config LIMIT 1")
                    row = cursor.fetchone()
                    conn.close()
                else:
                    import sqlite3
                    conn = sqlite3.connect('instance/gvn_algo_pro.db')
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
                        "broker_password": cipher.decrypt(row[2]).decode() if row[2] else "Gvn@12",
                        "client_secret": cipher.decrypt(row[3]).decode() if len(row) > 3 and row[3] else "",
                        "totp_key": cipher.decrypt(row[4]).decode() if row[4] else "",
                        "broker_name": row[5] or "Shoonya",
                        "active": True
                    })

            if shoonya_master_config.get('active'):
                for symbol in ["NIFTY", "BANKNIFTY"]:
                    analyze_and_update_gvn_scanner(symbol)
                    time.sleep(5)
            time.sleep(2)
        except Exception as e:
            time.sleep(10)

def start_live_feed_worker():
    broker = shoonya_master_config.get("broker_name", "Shoonya").upper()
    print(f"\n==================================================\n🔥 GVN MASTER ALGO: {broker} LIVE FEED ENGINE STARTING...\n==================================================\n")
    threading.Thread(target=live_feed_background_worker, daemon=True).start()
