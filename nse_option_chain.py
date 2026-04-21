import requests
import math
import time
from datetime import datetime
import threading

# Global memory to store the latest Delta 60 strikes per index
current_delta_60_strikes = {
    "NIFTY": {"CE": None, "PE": None},
    "BANKNIFTY": {"CE": None, "PE": None},
    "FINNIFTY": {"CE": None, "PE": None},
    "SENSEX": {"CE": None, "PE": None},
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

# --- NSE Data Fetching ---
def fetch_nse_option_chain(symbol="NIFTY"):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[NSE API] Exception: {e}")
        return None

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    global current_delta_60_strikes, gvn_scanner_data
    
    data = fetch_nse_option_chain(symbol)
    if not data or "records" not in data: return
        
    records = data["records"]
    underlying_value = records["underlyingValue"]
    expiry_dates = records["expiryDates"]
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

    for item in records["data"]:
        if item["expiryDate"] == nearest_expiry:
            strike = item["strikePrice"]
            
            for opt_type in ["CE", "PE"]:
                if opt_type in item:
                    opt = item[opt_type]
                    ltp = opt.get("lastPrice", 0)
                    iv = opt.get("impliedVolatility", 0)
                    
                    key = f"{int(strike)}_{opt_type}"
                    live_option_ltps[key] = ltp
                    
                    # Calculate Delta with Fallback
                    effective_iv = iv if iv > 0 else 18.0
                    delta = 0
                    try:
                        delta = abs(calculate_delta(underlying_value, strike, T, r, effective_iv/100.0, opt_type))
                    except:
                        delta = 0

                    # --- 🌟 DELTA 60 SELECTION ---
                    if abs(delta - 0.60) < (closest_ce_diff if opt_type == "CE" else closest_pe_diff):
                        if opt_type == "CE":
                            closest_ce_diff = abs(delta - 0.60)
                            best_ce_60 = strike
                        else:
                            closest_pe_diff = abs(delta - 0.60)
                            best_pe_60 = strike
                    
                    # --- 🚀 ZERO TO HERO SCANNER ---
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
        current_delta_60_strikes[symbol] = {"CE": int(best_ce_60), "PE": int(best_pe_60)}
        current_delta_60_strikes["last_updated"] = datetime.now().strftime("%H:%M:%S")

    # Sort & Truncate Scanner
    gvn_scanner_data[symbol] = sorted(gvn_scanner_data[symbol], key=lambda x: x["score"], reverse=True)[:10]
    gvn_scanner_data["last_updated"] = datetime.now().strftime("%H:%M:%S")
    
    print(f"📡 [NSE Worker] {symbol} Data Synced | Delta 60: CE={best_ce_60}, PE={best_pe_60}")

def nse_background_worker():
    while True:
        try:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: NSE Worker Pulse...\n")
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]:
                analyze_and_update_gvn_scanner(symbol)
                time.sleep(2) 
        except Exception as e:
            print(f"[NSE Worker Error] {e}")
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: ERROR: {str(e)}\n")
        time.sleep(10)

def start_nse_worker():
    # Immediate log to verify thread start
    with open("nse_status.log", "w") as f:
        f.write(f"{datetime.now()}: [INIT] NSE AI Engine Thread Initialized.\n")
        
    thread = threading.Thread(target=nse_background_worker, daemon=True)
    thread.start()
    print("[NSE AI Engine] Started Live Fibonacci Polling...")
