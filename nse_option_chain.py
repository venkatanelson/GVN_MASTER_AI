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
    # For SENSEX, we should use a different logic or skip if NSE-only
    if symbol == "SENSEX": return None 
    
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    try:
        # First hit the home page to get fresh cookies if needed
        if not nse_session.cookies:
            nse_session.get("https://www.nseindia.com", headers=nse_headers, timeout=10)
        
        response = nse_session.get(url, headers=nse_headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403 or response.status_code == 401:
            # Try Dhan Fallback if NSE is blocked
            return fetch_from_dhan_fallback(symbol)
        else:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [ERROR] {symbol} Fetch Failed. Status: {response.status_code}\n")
            return fetch_from_dhan_fallback(symbol)
    except Exception as e:
        return fetch_from_dhan_fallback(symbol)

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
        
        quote = dhan.get_quote(sid)
        if quote.get('status') == 'success':
            lp = quote['data'].get('lastPrice', 0)
            # Create a mock NSE-style response for basic spot tracking
            return {
                "records": {
                    "underlyingValue": lp,
                    "expiryDates": [], # Fallback doesn't have full chain yet
                    "data": []
                },
                "source": "DHAN_API"
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

    for item in records.get("data", []):
        if item.get("expiryDate") == nearest_expiry:
            strike = item.get("strikePrice")
            
            for opt_type in ["CE", "PE"]:
                if opt_type in item:
                    opt = item[opt_type]
                    ltp = opt.get("lastPrice", 0)
                    iv = opt.get("impliedVolatility", 0)
                    
                    key = f"{int(strike)}_{opt_type}"
                    live_option_ltps[key] = ltp
                    
                    # Update History for Balloon Pressure
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
                            elif ltp <= levels["Level_6"]: zone, score = "⚡ MOMENTUM ZONE (L6)", 35
                        else:
                            if ltp <= levels["Level_1"]: zone, score = "🚀 OTM BUY ZONE (L1)", 65
                            elif ltp <= levels["Level_7"]: zone, score = "📡 RADAR ZONE (L7)", 25
                        
                        if score > 0:
                            gvn_scanner_data[symbol].append({
                                "strike": f"{int(strike)} {opt_type}",
                                "ltp": ltp,
                                "delta": round(delta, 2),
                                "score": score,
                                "zone": zone,
                                "potential": "HIGH" if score >= 60 else "MODERATE",
                                "levels": levels
                            })

    # Update Global Strikes
    if best_ce_60 and best_pe_60:
        formatted_expiry = expiry_dt.strftime("%d %b").upper() # e.g. "25 APR"
        current_delta_60_strikes[symbol] = {
            "CE": int(best_ce_60), 
            "PE": int(best_pe_60),
            "expiry": formatted_expiry
        }
        current_delta_60_strikes["last_updated"] = datetime.now().strftime("%H:%M:%S")

    # Sort & Truncate
    gvn_scanner_data[symbol] = sorted(gvn_scanner_data[symbol], key=lambda x: x["score"], reverse=True)[:10]
    
    # Mark source
    source = data.get("source", "NSE_WEB")
    gvn_scanner_data["last_updated"] = datetime.now().strftime("%H:%M:%S") + f" ({source})"

def nse_background_worker():
    print("🚀 [NSE Worker] Thread Started Successfully.")
    while True:
        try:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: NSE Worker Pulse...\n")
            
            # Note: SENSEX is removed as it's not an NSE index
            # NIFTY, BANKNIFTY, FINNIFTY are NSE. SENSEX is BSE but we try fallback or dummy.
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]:
                analyze_and_update_gvn_scanner(symbol)
                time.sleep(3) # Respect NSE rate limits
                
        except Exception as e:
            print(f"[NSE Worker Error] {e}")
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: FATAL ERROR: {str(e)}\n")
        
        time.sleep(15)

def start_nse_worker():
    # Force reset session to clear stale cookies
    global nse_session
    nse_session = requests.Session()
    
    with open("nse_status.log", "w") as f:
        f.write(f"{datetime.now()}: [INIT] NSE AI Engine Thread Initialized.\n")
        
    thread = threading.Thread(target=nse_background_worker, daemon=True)
    thread.start()
    print("[NSE AI Engine] Started Live Fibonacci Polling...")

