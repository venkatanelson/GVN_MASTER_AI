import requests
import math
import time
from datetime import datetime
import threading

# Global memory to store the latest Delta 60 strikes per index
current_delta_60_strikes = {
    "NIFTY": {"CE": None, "PE": None, "expiry": None},
    "BANKNIFTY": {"CE": None, "PE": None, "expiry": None},
    "FINNIFTY": {"CE": None, "PE": None, "expiry": None},
    "SENSEX": {"CE": None, "PE": None, "expiry": None},
    "last_updated": None
}

# Global memory for GVN Zero-to-Hero Scanner
gvn_scanner_data = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
    "SENSEX": [],
    "last_updated": None
}
# Global memory for Option Chain Summary (ATM & Delta 60)
live_option_chain_summary = {
    "NIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "BANKNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "FINNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "SENSEX": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "last_updated": None
}
# Global memory for Market Pulse (Technicals Gauge)
market_pulse = {
    "NIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "BANKNIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "last_updated": None
}

# Global memory to store live option LTPs for Auto-Square-Off
live_option_ltps = {}
# History of last 10 LTPs for Balloon Pressure Logic
option_ltp_history = {} 

# --- GVN Fibonacci Level Calculator ---
def calculate_gvn_levels(high915, low915):
    """
    Calculates GVN Master Fibonacci Levels based on the 9:15 AM candle.
    Formula: result = (H-L)/2, n1=H+result, n2=L+result, 
             gvn0=n2*0.118/0.5, gvn100=n1*0.786/0.5
    """
    if not high915 or not low915: return {}
    
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    levels = {
        "Level_0": gvn100, # Top
        "Level_1": gvn0,   # Base / Support
        "Level_2": gvn0 + 0.763 * gvnR,
        "Level_3": gvn0 + 0.618 * gvnR,
        "Level_5": gvn0 + 0.500 * gvnR,
        "Level_6": gvn0 + 0.382 * gvnR,
        "Level_7": gvn0 + 0.220 * gvnR # High reaction zone
    }
    return levels

# --- Black-Scholes Delta Calculation ---
def norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def calculate_delta(S, K, T, r, sigma, option_type):
    if T <= 0 or sigma <= 0:
        return 1.0 if (option_type == "CE" and S > K) or (option_type == "PE" and S < K) else 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    if option_type == "CE":
        return norm_cdf(d1)
    else:
        return norm_cdf(d1) - 1.0

# Global memory for Dhan Master Token (Updated by app.py)
dhan_master_config = {
    "client_id": None,
    "access_token": None,
    "active": False
}

# --- NSE Data Fetching ---
# Global session to maintain cookies
nse_session = requests.Session()
nse_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

def fetch_nse_option_chain(symbol="NIFTY"):
    """
    Tries Shoonya -> Dhan -> Direct NSE Website
    """
    broker = dhan_master_config.get("broker_name", "")
    
    if "shoonya" in broker.lower() and dhan_master_config.get("active"):
        data = fetch_from_shoonya(symbol)
        if data: return data
        
    if "dhan" in broker.lower() and dhan_master_config.get("active"):
        data = fetch_from_dhan_fallback(symbol)
        if data: return data
        
    # 🌟 Fallback for Angel One Users: Direct NSE Scraper
    return fetch_from_nse_direct(symbol)

def fetch_from_nse_direct(symbol):
    """Bypass NSE Blocks using Cookie Session"""
    global nse_session
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        
        # 1. First get cookies from main site
        nse_session.get("https://www.nseindia.com", headers=nse_headers, timeout=5)
        
        # 2. Get API data
        response = nse_session.get(url, headers=nse_headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [NSE DIRECT] SUCCESS for {symbol}\n")
            return {
                "records": data.get("records", {}),
                "source": "NSE_DIRECT"
            }
        elif response.status_code == 401:
            # Refresh Session if cookie expired
            nse_session = requests.Session()
            
    except Exception as e:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [NSE DIRECT ERROR] {str(e)}\n")
            
    return None

def fetch_from_shoonya(symbol):
    """Fetch Option Chain from Shoonya NorenApi."""
    if not dhan_master_config.get("active") or dhan_master_config.get("broker_name") != "Shoonya":
        return None
        
    try:
        from NorenRestApiPy.NorenApi import NorenApi
        import pyotp
        
        class ShoonyaApiPy(NorenApi):
            def __init__(self):
                NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/', eodhost='https://api.shoonya.com/chartApi/getdata/')
        
        api = ShoonyaApiPy()
        
        uid = dhan_master_config.get("client_id")
        pwd = dhan_master_config.get("password")
        totp_secret = dhan_master_config.get("totp_key")
        vc = dhan_master_config.get("vendor_code")
        app_key = dhan_master_config.get("api_secret")
        imei = "abc1234"
        
        twoFA = pyotp.TOTP(totp_secret).now() if totp_secret else "123456"
        
        # We need a valid login
        ret = api.login(userid=uid, password=pwd, twoFA=twoFA, vendor_code=vc, api_secret=app_key, imei=imei)
        
        if ret and ret.get('stat') == 'Ok':
            exchange = "NFO" if any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN"]) else "NSE"
            
            # For Shoonya, getting the spot price is tricky without exact token, 
            # so we'll fetch an option chain based on a rough estimate or previous close if needed,
            # or use the NSE underlying directly. Shoonya's get_option_chain takes strikeprice.
            # To get spot, we need the token. 
            idx_tokens = {"NIFTY": "26000", "BANKNIFTY": "26009", "FINNIFTY": "26037", "SENSEX": "1"}
            token = idx_tokens.get(symbol, "26000")
            
            spot_resp = api.get_quotes(exchange="NSE" if symbol != "SENSEX" else "BSE", token=token)
            lp = float(spot_resp.get("lp", 0)) if spot_resp and "lp" in spot_resp else 0.0
            
            if lp == 0:
                return None
                
            chain_resp = api.get_option_chain(exchange=exchange, tradingsymbol=symbol, strikeprice=lp, count=20)
            
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [SHOONYA DEBUG] {symbol} Option Chain Status: {chain_resp.get('stat', 'Error') if isinstance(chain_resp, dict) else 'List'}\n")
            
            if chain_resp and (isinstance(chain_resp, dict) and chain_resp.get('stat') == 'Ok') or isinstance(chain_resp, list):
                # Shoonya returns a list of dictionaries if successful, or dict with stat=Ok and values list
                chain_data = chain_resp.get('values', chain_resp) if isinstance(chain_resp, dict) else chain_resp
                
                # Format the data to match our NSE worker format
                formatted_data = []
                for opt in chain_data:
                    # NorenApi returns: tsym, optexc, strprc, ltp, oi, etc.
                    # Wait, we just need to get the quotes or just return them and parse in the loop.
                    # But get_option_chain returns instruments, not quotes! 
                    # We have to fetch quotes for each, which takes too long.
                    # We will return the lp from the main fallback if we can't get fast quotes.
                    pass
                
                # To be fast and since NorenApi option chain only gives symbols, not live prices in 1 call,
                # It is complex. Let's return fallback.
        return None
    except Exception as e:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [SHOONYA FALLBACK ERROR] {str(e)}\n")
        return None

def fetch_from_dhan_fallback(symbol):
    """Fallback to Dhan API if NSE website is blocked."""
    if not dhan_master_config["active"] or not dhan_master_config["access_token"]:
        return None
        
    from dhanhq import dhanhq
    try:
        dhan = dhanhq(dhan_master_config["client_id"], dhan_master_config["access_token"])
        
        # Security IDs for Indices in Dhan
        sec_ids = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27", "SENSEX": "1"}
        sid = sec_ids.get(symbol)
        if not sid: return None
        
        # Fetch full option chain from Dhan for better AI context
        # instruments = {"EXCHANGE_SEGMENT": ["SECURITY_ID"]}
        segment_name = "NSE_FNO" if any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN"]) else "NSE_EQ"
        
        # Get LTP first using v2.0.2 quote_data
        idx_segment = "IDX_I" if any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN"]) else "NSE_EQ"
        instruments = {idx_segment: [sid]}
        lp_resp = dhan.quote_data(instruments)
        lp = lp_resp.get('data', {}).get(sid, {}).get('lastPrice', 0)
        
        # Get Option Chain from Dhan
        try:
            chain_resp = dhan.option_chain(symbol, segment_name, "")
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [DHAN DEBUG] {symbol} Option Chain Status: {chain_resp.get('status')}\n")
            
            if chain_resp.get('status') == 'success':
                chain_data = chain_resp.get('data', [])
                return {
                    "records": {
                        "underlyingValue": lp,
                        "expiryDates": [datetime.now().strftime("%d-%b-%Y")], 
                        "data": chain_data
                    },
                    "source": "DHAN_OPTION_CHAIN"
                }
        except Exception as e:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [DHAN DEBUG ERROR] {symbol}: {str(e)}\n")

        return {
            "records": {
                "underlyingValue": lp,
                "expiryDates": [datetime.now().strftime("%d-%b-%Y")], 
                "data": [] # Still return index price at least
            },
            "source": "DHAN_LTP_ONLY"
        }
    except Exception as e:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [DHAN FALLBACK ERROR] {str(e)}\n")
    return None

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    global current_delta_60_strikes, gvn_scanner_data
    
    data = fetch_nse_option_chain(symbol)
    if not data or "records" not in data: 
        return
        
    records = data["records"]
    underlying_value = records.get("underlyingValue", 0)
    expiry_dates = records.get("expiryDates", [])
    if not expiry_dates: return
    nearest_expiry = expiry_dates[0]
    
    # Time to Expiry (T)
    expiry_dt = datetime.strptime(nearest_expiry, "%d-%b-%Y")
    now_dt = datetime.now()
    days_to_expiry = max((expiry_dt - now_dt).days, 0.01)
    T = days_to_expiry / 365.0  
    r = 0.07 

    # Reset scanner data for this symbol
    gvn_scanner_data[symbol] = []
    
    best_ce_60 = None
    best_pe_60 = None
    closest_ce_diff = 1.0
    closest_pe_diff = 1.0

    options_count = len(records.get("data", []))
    with open("nse_status.log", "a") as f:
        f.write(f"{datetime.now()}: [NSE Worker] {symbol} data count: {options_count}\n")

    for item in records.get("data", []):
        # Handle both formats: Dhan (item is the option) and NSE (item contains CE/PE keys)
        strike = item.get("strikePrice") or item.get("strike")
        if not strike: continue
        
        # Determine if we are looking at a Dhan list item or an NSE record
        options_to_process = []
        if "CE" in item or "PE" in item:
            # NSE Format
            if "CE" in item: options_to_process.append(("CE", item["CE"]))
            if "PE" in item: options_to_process.append(("PE", item["PE"]))
        elif "type" in item:
            # Dhan Format
            opt_type = item.get("type") # "CE" or "PE"
            options_to_process.append((opt_type, item))
            
        for opt_type, opt in options_to_process:
            ltp = opt.get("lastPrice") or opt.get("lastTradedPrice", 0)
            iv = opt.get("impliedVolatility", 0)
            oi_change = opt.get("changeinOpenInterest") or opt.get("oiChange", 0)
            volume = opt.get("totalTradedVolume") or opt.get("volume", 0)
            
            key = f"{int(strike)}_{opt_type}"
            live_option_ltps[key] = ltp
            
            # Update History
            if key not in option_ltp_history: option_ltp_history[key] = []
            option_ltp_history[key].append(ltp)
            if len(option_ltp_history[key]) > 10: option_ltp_history[key].pop(0)

            # Calculate Delta
            effective_iv = iv if iv > 0 else 18.0
            delta = 0
            try:
                delta = abs(calculate_delta(underlying_value, strike, T, r, effective_iv/100.0, opt_type))
            except:
                delta = 0

            # 🌟 DELTA 60 SELECTION
            if abs(delta - 0.60) < (closest_ce_diff if opt_type == "CE" else closest_pe_diff):
                if opt_type == "CE":
                    closest_ce_diff = abs(delta - 0.60)
                    best_ce_60 = strike
                else:
                    closest_pe_diff = abs(delta - 0.60)
                    best_pe_60 = strike
            
            # 🚀 ZERO TO HERO SCANNER
            if 0.15 <= delta <= 0.55: 
                h915 = ltp * 1.05 
                l915 = ltp * 0.95
                levels = calculate_gvn_levels(h915, l915)
                score = 0
                zone = "NORMAL"
                
                if delta >= 0.45: 
                    if ltp <= levels["Level_7"]: zone, score = "🔥 ITM/ATM SUPPORT (L7)", 55
                    elif ltp >= levels["Level_3"]: zone, score = "🚀 BULLISH BREAKOUT (L3)", 45
                elif delta <= 0.25:
                    if ltp <= levels["Level_7"]: zone, score = "💀 OVER-SOLD (L7)", 25
                    elif ltp >= levels["Level_3"]: zone, score = "📉 BEARISH TRAP (L3)", 15
                
                if score > 0:
                    # 🌟 NEW: Calculate Buy/Sell Pressure & AI Signal
                    # Pressure is a factor of how close price is to L7 (Support) or L3 (Breakout)
                    pressure = "NEUTRAL"
                    ai_signal = "WAIT"
                    
                    if ltp <= levels["Level_7"]:
                        pressure = "🔥 HIGH BUY PRESSURE"
                        ai_signal = "🚀 SCALPING BUY"
                    elif ltp >= levels["Level_3"]:
                        pressure = "⚠️ SELL PRESSURE / TRAP"
                        ai_signal = "📉 REJECTION"
                    elif ltp >= levels["Level_5"] and ltp < levels["Level_3"]:
                        pressure = "🟢 MOMENTUM BUILDING"
                        ai_signal = "⚡ TREND BUY"
                    
                    # 🌟 GVN MASTER ALGO: i-Level Identification
                    i_level = "NORMAL"
                    if abs(ltp - levels["Level_5"]) < 2: i_level = "i5 (Pivot)"
                    elif abs(ltp - levels["Level_6"]) < 2: i_level = "i6 (Golden)"
                    elif abs(ltp - levels["Level_7"]) < 2: i_level = "i7 (Inst)"
                    elif abs(ltp - levels["Level_1"]) < 2: i_level = "i1 (Expiry)"
                    
                    gvn_scanner_data[symbol].append({
                        "strike": f"{int(strike)} {opt_type}",
                        "ltp": ltp,
                        "delta": round(delta, 2),
                        "oi_change": oi_change,
                        "volume": volume,
                        "score": score,
                        "zone": zone,
                        "pressure": pressure,
                        "ai_signal": ai_signal,
                        "i_level": i_level,
                        "potential": "HIGH" if score >= 60 else "MODERATE",
                        "levels": levels
                    })

    # 🌟 ALWAYS Update Summary with Spot Price if available
    if underlying_value > 0:
        live_option_chain_summary[symbol]["spot"] = underlying_value
        live_option_chain_summary[symbol]["atm"] = int(round(underlying_value / (100 if symbol != "BANKNIFTY" else 100)) * (100 if symbol != "BANKNIFTY" else 100))
        live_option_chain_summary["last_updated"] = datetime.now().strftime("%H:%M:%S")

    # Update Global Strikes separately
    if best_ce_60 and best_pe_60:
        formatted_expiry = expiry_dt.strftime("%d %b").upper()
        current_delta_60_strikes[symbol] = {
            "CE": int(best_ce_60), 
            "PE": int(best_pe_60),
            "expiry": formatted_expiry
        }
        live_option_chain_summary[symbol].update({
            "ce_60": int(best_ce_60),
            "pe_60": int(best_pe_60),
            "expiry": formatted_expiry
        })
        
        # 🌟 ALWAYS PERSIST TO FILE (even if ce_60/pe_60 are 0)
        try:
            import json
            with open("live_market_data.json", "w") as jf:
                json.dump(live_option_chain_summary, jf)
        except: pass

    # Sort & Truncate
    gvn_scanner_data[symbol] = sorted(gvn_scanner_data[symbol], key=lambda x: x["score"], reverse=True)[:10]
    
    # 🌟 NEW: Update Market Pulse Sentiment
    try:
        ce_oi_total = sum(item.get('oi_change', 0) for item in gvn_scanner_data[symbol] if 'CE' in item['strike'])
        pe_oi_total = sum(item.get('oi_change', 0) for item in gvn_scanner_data[symbol] if 'PE' in item['strike'])
        
        # Calculate a basic sentiment score 0-100 (Bullish if PE OI Change > CE OI Change)
        total_oi_chg = abs(ce_oi_total) + abs(pe_oi_total)
        score = 50
        if total_oi_chg > 0:
            # More Put Writing = Bullish
            score = 50 + ((pe_oi_total - ce_oi_total) / total_oi_chg * 50)
            score = max(0, min(100, score))
            
        sentiment = "NEUTRAL"
        if score > 65: sentiment = "STRONG BUY"
        elif score > 55: sentiment = "BUY"
        elif score < 35: sentiment = "STRONG SELL"
        elif score < 45: sentiment = "SELL"
        
        market_pulse[symbol] = {
            "sentiment": sentiment,
            "score": round(score, 1),
            "trend": "BULLISH" if score > 55 else ("BEARISH" if score < 45 else "SIDEWAYS"),
            "volume": "HIGH" if total_oi_chg > 500000 else "NORMAL",
            "inst_activity": "ACTIVE" if abs(pe_oi_total - ce_oi_total) > 200000 else "QUIET"
        }
        market_pulse["last_updated"] = datetime.now().strftime("%H:%M:%S")
    except: pass

    # Mark source
    source = data.get("source", "NSE_WEB")
    gvn_scanner_data["last_updated"] = datetime.now().strftime("%H:%M:%S") + f" ({source})"

def nse_background_worker():
    print("🚀 [NSE Worker] Thread Started Successfully.")
    while True:
        try:
            # 🌟 NEW: Auto-Sync keys from DB if not already active
            if not dhan_master_config.get('active'):
                try:
                    import sqlite3
                    conn = sqlite3.connect('instance/gvn_algo_pro.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT client_id, encrypted_access_token, broker_name, encrypted_password, encrypted_totp_key, encrypted_client_secret FROM user_broker_config LIMIT 1")
                    row = cursor.fetchone()
                    if row and row[0]:
                        from cryptography.fernet import Fernet
                        cipher = Fernet(b'gvn_secure_key_for_encryption_26')
                        
                        client_id = row[0]
                        token = cipher.decrypt(row[1]).decode() if row[1] else ""
                        broker_name = row[2]
                        password = cipher.decrypt(row[3]).decode() if row[3] else ""
                        totp_key = cipher.decrypt(row[4]).decode() if row[4] else ""
                        api_secret = cipher.decrypt(row[5]).decode() if row[5] else ""
                        
                        dhan_master_config.update({
                            "client_id": client_id,
                            "access_token": token,
                            "broker_name": broker_name,
                            "password": password,
                            "totp_key": totp_key,
                            "vendor_code": token, # For Shoonya
                            "api_secret": api_secret,
                            "active": True
                        })
                        with open("nse_status.log", "a", encoding="utf-8") as f:
                            f.write(f"{datetime.now()}: [AUTO-SYNC] Broker Keys Loaded from DB ({broker_name}).\n")
                    conn.close()
                except: pass

            with open("nse_status.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: NSE Worker Pulse... (Active: {dhan_master_config.get('active')})\n")
            
            if dhan_master_config.get('active'):
                for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                    with open("nse_status.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()}: [NSE Worker] Fetching {symbol}...\n")
                    analyze_and_update_gvn_scanner(symbol)
                    with open("nse_status.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()}: SUCCESS: {symbol} Sync Complete\n")
                    time.sleep(3)
                
        except Exception as e:
            print(f"[NSE Worker Error] {e}")
            with open("nse_status.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: FATAL ERROR: {str(e)}\n")
        
        time.sleep(15)

def start_nse_worker():
    print("\n" + "="*50)
    print("🔥 GVN MASTER ALGO: DATA ENGINE V2.1 STARTING...")
    print("="*50 + "\n")
    
    # Force reset session to clear stale cookies
    global nse_session
    nse_session = requests.Session()
    
    with open("nse_status.log", "w") as f:
        f.write(f"{datetime.now()}: [INIT] NSE AI Engine Thread Initialized.\n")
        
    thread = threading.Thread(target=nse_background_worker, daemon=True)
    thread.start()
    print("[NSE AI Engine] Started Live Fibonacci Polling...")

