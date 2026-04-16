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

# --- Black-Scholes Delta Calculation ---
def norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def calculate_delta(S, K, T, r, sigma, option_type):
    """
    Calculate Option Delta using Black-Scholes.
    S: Spot Price
    K: Strike Price
    T: Time to Expiry (in years)
    r: Risk-free rate (approx 0.07 for India usually, but we use 0.0)
    sigma: Implied Volatility (IV / 100)
    option_type: "CE" or "PE"
    """
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
        # First request to get cookies
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        # Second request to get the actual JSON
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[NSE API] Error: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"[NSE API] Exception: {e}")
        return None

def analyze_and_find_delta_60():
    global current_delta_60_strikes
    
    data = fetch_nse_option_chain()
    if not data or "records" not in data:
        return
        
    records = data["records"]
    underlying_value = records["underlyingValue"]
    
    # Find the nearest expiry
    expiry_dates = records["expiryDates"]
    if not expiry_dates:
        return
    nearest_expiry = expiry_dates[0]
    
    # Parse date for Time to Expiry (T)
    # Expiry format: '25-Apr-2026'
    expiry_dt = datetime.strptime(nearest_expiry, "%d-%b-%Y")
    now_dt = datetime.now()
    days_to_expiry = (expiry_dt - now_dt).days
    # If today is expiry, set a minimal fraction of a day to avoid Division By Zero
    T = max(days_to_expiry, 0.01) / 365.0  
    
    r = 0.07 # Risk free rate approx 7%
    
    best_ce_strike = None
    best_pe_strike = None
    closest_ce_diff = 100
    closest_pe_diff = 100

    for item in records["data"]:
        if item["expiryDate"] == nearest_expiry:
            strike = item["strikePrice"]
            
            # Analyze CE
            if "CE" in item:
                iv_ce = item["CE"].get("impliedVolatility", 0)
                if iv_ce > 0:
                    sigma_ce = iv_ce / 100.0
                    delta_ce = calculate_delta(underlying_value, strike, T, r, sigma_ce, "CE")
                    
                    diff = abs(delta_ce - 0.60)
                    if diff < closest_ce_diff:
                        closest_ce_diff = diff
                        best_ce_strike = strike

            # Analyze PE
            if "PE" in item:
                iv_pe = item["PE"].get("impliedVolatility", 0)
                if iv_pe > 0:
                    sigma_pe = iv_pe / 100.0
                    pe_delta_mag = abs(calculate_delta(underlying_value, strike, T, r, sigma_pe, "PE"))
                    
                    diff = abs(pe_delta_mag - 0.60)
                    if diff < closest_pe_diff:
                        closest_pe_diff = diff
                        best_pe_strike = strike

    if best_ce_strike and best_pe_strike:
        current_delta_60_strikes["CE"] = int(best_ce_strike)
        current_delta_60_strikes["PE"] = int(best_pe_strike)
        current_delta_60_strikes["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[NSE AI] LIVE Updated: Spot={underlying_value} | Best CE 0.6 Delta={best_ce_strike} | Best PE 0.6 Delta={best_pe_strike}")

def nse_background_worker():
    """Runs continuously in the background fetching data every 3 minutes."""
    while True:
        try:
            analyze_and_find_delta_60()
        except Exception as e:
            print(f"[NSE Worker Error] {e}")
        time.sleep(180) # Refresh every 3 mins to avoid NSE blocking

def start_nse_worker():
    thread = threading.Thread(target=nse_background_worker, daemon=True)
    thread.start()
    print("[NSE AI Engine] Started Live Polling...")
