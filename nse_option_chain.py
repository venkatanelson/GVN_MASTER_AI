import requests
import math
import time
from datetime import datetime
import threading

# Global memory to store the latest Delta 60 strikes
current_delta_60_strikes = {
    "CE": None,
    "PE": None,
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

    strikes_pool = []
    
    # Delta 60 logic remains for main execution
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
                    vol = opt.get("totalTradedVolume", 0)
                    oi_chg = opt.get("changeinOpenInterest", 0)
                    
                    key = f"{int(strike)}_{opt_type}"
                    live_option_ltps[key] = ltp
                    
                    # History for Balloon Pressure
                    if key not in option_ltp_history: option_ltp_history[key] = []
                    option_ltp_history[key].append(ltp)
                    if len(option_ltp_history[key]) > 10: option_ltp_history[key].pop(0)

                    if iv > 0:
                        sigma = iv / 100.0
                        delta = abs(calculate_delta(underlying_value, strike, T, r, sigma, opt_type))
                        
                        # --- 🌟 DELTA 60 SELECTION ---
                        if abs(delta - 0.60) < (closest_ce_diff if opt_type == "CE" else closest_pe_diff):
                            if opt_type == "CE":
                                closest_ce_diff = abs(delta - 0.60)
                                best_ce_60 = strike
                            else:
                                closest_pe_diff = abs(delta - 0.60)
                                best_pe_60 = strike
                        
                        # --- 🚀 ZERO TO HERO SCANNER (Delta 0.20 - 0.50) ---
                        # --- 🚀 ZERO TO HERO SCANNER (Expanded Multi-Index) ---
                        if 0.15 <= delta <= 0.55: # Slightly wider range for better ITM/OTM coverage
                            h915 = ltp * 1.05 
                            l915 = ltp * 0.95
                            levels = calculate_gvn_levels(h915, l915)
                            
                            score = 0
                            zone = "NORMAL"
                            
                            # ITM/ATM Logic: Level 7 or Level 6
                            if delta >= 0.45: 
                                if ltp <= levels["Level_7"]:
                                    zone = "🔥 ITM/ATM SUPPORT (L7)"
                                    score += 55
                                elif ltp <= levels["Level_6"]:
                                    zone = "⚡ MOMENTUM ZONE (L6)"
                                    score += 40
                            # OTM Logic: Level 1 Rejection
                            else:
                                if ltp <= levels["Level_1"]: 
                                    zone = "🚀 OTM BUY ZONE (L1)"
                                    score += 60
                                elif ltp <= levels["Level_7"]:
                                    zone = "⚡ OTM ENTRY (L7)"
                                    score += 30
                            
                            if vol > 50000: score += 15
                            if oi_chg > 0: score += 10
                            
                            final_score = min(100, score)
                            potential = "MODERATE"
                            if final_score >= 80: potential = "VERY HIGH 💎"
                            elif final_score >= 50: potential = "HIGH 🔥"

                            strikes_pool.append({
                                "strike": f"{int(strike)} {opt_type}",
                                "ltp": ltp,
                                "delta": round(delta, 2),
                                "zone": zone,
                                "score": final_score,
                                "potential": potential,
                                "levels": levels
                            })

    # Update Global Memory
    if best_ce_60 and best_pe_60:
        current_delta_60_strikes["CE"] = int(best_ce_60)
        current_delta_60_strikes["PE"] = int(best_pe_60)
        current_delta_60_strikes["last_updated"] = datetime.now().strftime("%H:%M:%S")

    # Sort and take top 5 CE and 5 PE for scanner
    ce_strikes = sorted([s for s in strikes_pool if "CE" in s["strike"]], key=lambda x: x["delta"], reverse=True)[:5]
    pe_strikes = sorted([s for s in strikes_pool if "PE" in s["strike"]], key=lambda x: x["delta"], reverse=True)[:5]
    
    gvn_scanner_data[symbol] = ce_strikes + pe_strikes
    gvn_scanner_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[NSE SCANNER] {symbol} Updated | Strikes Monitored: {len(gvn_scanner_data[symbol])}")

def nse_background_worker():
    while True:
        try:
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                analyze_and_update_gvn_scanner(symbol)
                time.sleep(2) # Small delay between index updates
        except Exception as e:
            print(f"[NSE Worker Error] {e}")
        time.sleep(10)

def start_nse_worker():
    thread = threading.Thread(target=nse_background_worker, daemon=True)
    thread.start()
    print("[NSE AI Engine] Started Live Fibonacci Polling...")
