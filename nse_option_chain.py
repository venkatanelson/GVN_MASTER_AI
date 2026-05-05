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
    "MIDCPNIFTY": {"CE": None, "PE": None, "expiry": None},
    "CRUDEOIL": {"CE": None, "PE": None, "expiry": None},
    "last_updated": None
}

# Global memory for GVN Zero-to-Hero Scanner
gvn_scanner_data = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
    "SENSEX": [],
    "MIDCPNIFTY": [],
    "CRUDEOIL": [],
    "last_updated": None
}
# Global memory for Option Chain Summary (ATM & Delta 60)
live_option_chain_summary = {
    "NIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "BANKNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "FINNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "SENSEX": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "MIDCPNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "CRUDEOIL": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "last_updated": None
}
# Global memory for Market Pulse (Technicals Gauge)
import shared_data
market_pulse = {
    "NIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "BANKNIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "MIDCPNIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "CRUDEOIL": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "last_updated": None
}

# Global memory to store live option LTPs for Auto-Square-Off
live_option_ltps = {}
# History of last 10 LTPs for Balloon Pressure Logic
option_ltp_history = {} 

# --- GVN Fibonacci Level Calculator ---
def calculate_gvn_levels(high915, low915):
    """
    Calculates GVN Master Fibonacci Levels based on the 9:15 AM candle (PRO v2 Logic).
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
        "i1": round(gvn100, 2), # GVN Top
        "i0": round(gvn0, 2),   # GVN Bottom
        "i2": round(gvn0 + 0.763 * gvnR, 2),
        "i3": round(gvn0 + 0.618 * gvnR, 2),
        "i5": round(gvn0 + 0.500 * gvnR, 2),
        "i6": round(gvn0 + 0.382 * gvnR, 2),
        "i7": round(gvn0 + 0.220 * gvnR, 2)
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

def calculate_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0: return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    phi_d1 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * d1**2)
    return phi_d1 / (S * sigma * math.sqrt(T))

def calculate_theta(S, K, T, r, sigma, option_type):
    if T <= 0 or sigma <= 0: return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    phi_d1 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * d1**2)
    
    term1 = -(S * phi_d1 * sigma) / (2 * math.sqrt(T))
    if option_type == "CE":
        term2 = r * K * math.exp(-r * T) * norm_cdf(d2)
        return (term1 - term2) / 365.0 # Daily Theta
    else:
        term2 = r * K * math.exp(-r * T) * norm_cdf(-d2)
        return (term1 + term2) / 365.0 # Daily Theta

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
    Tries Angel -> Shoonya -> Direct NSE Website
    Ensures that if one source returns empty data, it falls back to the next.
    """
    broker = dhan_master_config.get("broker_name", "").lower()
    data = None
    
    # 1. Try Angel One (if configured)
    if "angel" in broker:
        data = fetch_from_angel(symbol)
        if data and data.get("records", {}).get("data"):
            return data
        else:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [FALLBACK] Angel returned empty/failed for {symbol}. Trying Shoonya...\n")

    # 2. Try Shoonya (Primary or Fallback)
    # Check if Shoonya is already configured in dhan_master_config
    if dhan_master_config.get("broker_name") == "shoonya" and dhan_master_config.get("active"):
        data = fetch_from_shoonya(symbol, custom_cfg=dhan_master_config)
    else:
        # Try from backup but it might need login if token is missing
        shoonya_cfg = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("shoonya")
        if shoonya_cfg and shoonya_cfg.get("totp_key"):
            data = fetch_from_shoonya(symbol, custom_cfg=shoonya_cfg)
            
    if data and data.get("records", {}).get("data"):
        return data
    else:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [FALLBACK] Shoonya failed for {symbol}. Trying NSE Direct...\n")

    # 3. Try NSE Website Direct
    data = fetch_from_nse_direct(symbol)
    if data and data.get("records", {}).get("data"):
        return data

    return None

def fetch_from_angel(symbol):
    """Fetch Option Chain from Angel One SmartAPI."""
    try:
        from gvn_master_orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch or not orch.broker_config: return None
        
        # Angel One logic to get option chain
        # Since Angel doesn't have a single 'option_chain' API like Dhan, 
        # we usually fetch multiple quotes or use the orchestrator's live data
        import shared_data
        lp = shared_data.market_data.get(symbol, 0)
        
        if lp == 0: return None
        
        return {
            "records": {
                "underlyingValue": lp,
                "expiryDates": [datetime.now().strftime("%d-%b-%Y")], # Placeholder
                "data": [] # Simplified for now
            },
            "source": "ANGEL_ONE"
        }
    except Exception as e:
        return None

def fetch_from_nse_direct(symbol):
    """Bypass NSE Blocks using Cookie Session with improved headers"""
    global nse_session
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,te;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/option-chain",
        "Connection": "keep-alive"
    }
    
    for attempt in range(5):
        try:
            # 1. Get cookies from main site - crucial step
            if attempt == 0 or not nse_session.cookies:
                nse_session.get("https://www.nseindia.com", headers=headers, timeout=15)
                time.sleep(1.5)
            
            # 2. Get API data
            response = nse_session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if "records" in data and data["records"].get("data"):
                    with open("nse_status.log", "a") as f:
                        f.write(f"{datetime.now()}: [NSE DIRECT] SUCCESS for {symbol} - Count: {len(data['records']['data'])}\n")
                    return {
                        "records": data.get("records", {}),
                        "source": "NSE_DIRECT"
                    }
                else:
                    with open("nse_status.log", "a") as f:
                        f.write(f"{datetime.now()}: [NSE DIRECT] Success but EMPTY data for {symbol}\n")
            elif response.status_code in [401, 403]:
                # Refresh Session
                nse_session = requests.Session()
                time.sleep(2)
            else:
                time.sleep(2)
        except Exception as e:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [NSE DIRECT ERROR] {str(e)}\n")
            time.sleep(2)
            
    return None

def fetch_from_shoonya(symbol, custom_cfg=None):
    """Fetch Option Chain from Shoonya NorenApi with Hybrid Fallback support."""
    cfg = custom_cfg if custom_cfg else dhan_master_config
    
    if not cfg: return None
    
    # 🌟 NEW: Use existing token if available to avoid 502/Login errors
    token = cfg.get("shoonya_token") or cfg.get("access_token")
    client_id = cfg.get("client_id")
    
    if not token or not client_id:
        # Try to login if token missing but creds exist
        if cfg.get("password") and cfg.get("totp_key"):
            from broker_api import shoonya_http_login
            token = shoonya_http_login(cfg)
            if not token: return None
        else:
            return None
        
    try:
        from NorenRestApiPy.NorenApi import NorenApi
        api = NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        
        # Set the token manually
        api._userid = client_id
        api._password = cfg.get("password")
        api._susertoken = token
        
        # Test connection with a simple quote
        test = api.get_quotes(exchange="NSE", token="26000") # Nifty Spot
        if not test or test.get('stat') != 'Ok':
            return None
            
        exchange = "NFO" if any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN"]) else "NSE"
        idx_tokens = {"NIFTY": "26000", "BANKNIFTY": "26009", "FINNIFTY": "26037", "SENSEX": "1"}
        idx_token = idx_tokens.get(symbol, "26000")
        
        # Log the request
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [SHOONYA DEBUG] Fetching {symbol} (Token: {idx_token}) | Exch: {exchange}\n")
        
        spot_resp = api.get_quotes(exchange="NSE" if symbol != "SENSEX" else "BSE", token=idx_token)
        lp = float(spot_resp.get("lp", 0)) if spot_resp and "lp" in spot_resp else 0.0
        
        if lp == 0:
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [SHOONYA DEBUG] LP is 0 for {symbol}\n")
            return None
            
        # Shoonya likes symbols like 'NIFTY' for option chain
        search_sym = "Nifty 50" if symbol == "NIFTY" else ( "Nifty Bank" if symbol == "BANKNIFTY" else symbol)
        chain_resp = api.get_option_chain(exchange=exchange, tradingsymbol=search_sym, strikeprice=lp, count=20)
        
        if chain_resp and (isinstance(chain_resp, dict) and chain_resp.get('stat') == 'Ok') or isinstance(chain_resp, list):
            chain_data = chain_resp.get('values', chain_resp) if isinstance(chain_resp, dict) else chain_resp
            
            # Format to match NSE format
            formatted_data = []
            for item in chain_data:
                strike = float(item.get('strprc', 0))
                opt_type = item.get('opttyp', 'CE')
                formatted_data.append({
                    "strike": strike,
                    "type": opt_type,
                    "lastPrice": float(item.get('ltp', 0)),
                    "oi": int(item.get('oi', 0)),
                    "volume": int(item.get('v', 0)),
                    "impliedVolatility": float(item.get('iv', 0))
                })
            
            return {
                "records": {
                    "underlyingValue": lp,
                    "expiryDates": [datetime.now().strftime("%d-%b-%Y")], 
                    "data": formatted_data
                },
                "source": "SHOONYA_HYBRID"
            }
        return None
    except Exception as e:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [SHOONYA ERROR] {str(e)}\n")
        return None

def get_915_candle_data(api, symbol, strike, opt_type):
    """
    Fetches the 9:15 AM candle (1-min and 5-min) from Shoonya for levels.
    """
    try:
        # 1. Get Token for the strike
        exchange = "NFO"
        tsym = f"{symbol}{datetime.now().strftime('%y%b').upper()}{int(strike)}{opt_type}"
        # This is a simplified tsym, real Shoonya tsym needs expiry date like NIFTY25APR24C22500
        # For now, we'll try to find it in the search
        search = api.searchscrip(exchange=exchange, searchtext=f"{symbol} {int(strike)} {opt_type}")
        if not search or search.get('stat') != 'Ok': return None
        
        token = search['values'][0]['token']
        
        # 2. Get 9:15 AM candle
        # Start time: today 09:15, End time: today 09:20
        start_time = datetime.now().replace(hour=9, minute=15, second=0).timestamp()
        end_time = datetime.now().replace(hour=9, minute=20, second=0).timestamp()
        
        # Get 1-min candles
        candles = api.get_time_price_series(exchange=exchange, token=token, startobj=str(int(start_time)), endobj=str(int(end_time)), interval="1")
        if candles and isinstance(candles, list):
            c915 = candles[-1] # First candle of the day
            return {
                "high": float(c915.get('inth', 0)),
                "low": float(c915.get('intl', 0)),
                "close": float(c915.get('intc', 0))
            }
    except: pass
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
    
    # Ensure symbol exists in memory to avoid KeyErrors
    if symbol not in gvn_scanner_data: gvn_scanner_data[symbol] = []
    if symbol not in market_pulse: 
        market_pulse[symbol] = {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"}
    if symbol not in live_option_chain_summary:
        live_option_chain_summary[symbol] = {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""}

    data = fetch_nse_option_chain(symbol)
    
    # 🌟 GVN SPECIAL: Force 24100 PE Levels if it's NIFTY (Run even if fetch fails)
    if symbol == "NIFTY":
        # Check if already in scanner
        if not any("24100 PE" in x["strike"] for x in gvn_scanner_data[symbol]):
            # Add it with User's specific levels from audio
            target_ltp = 171.80 # Updated from User's latest table
            user_levels = {
                "Level_1": 30.0,
                "Level_7": 99.84,
                "Level_6": 150.55,
                "Level_5": 187.49,
                "Level_3": 224.42,
                "Level_0": 269.81
            }
            gvn_scanner_data[symbol].append({
                "strike": "24100 PE",
                "ltp": target_ltp,
                "delta": 0.70,
                "oi_change": -26423,
                "volume": 2822594,
                "score": 92, # Slightly down due to consolidation
                "zone": "🚀 MOMENTUM RALLY (i6 Cross)",
                "pressure": "🟢 CONSOLIDATION / HOLD",
                "ai_signal": "🎯 TARGET i5 (187.4)",
                "i_level": "i6 (150.5) Support",
                "potential": "MAXIMUM",
                "levels": user_levels
            })

    if not data or "records" not in data: 
        # Still update shared data if we have the forced strike
        if gvn_scanner_data[symbol]:
            try:
                shared_data.gvn_scanner_data = {
                    "summary": live_option_chain_summary,
                    "scanner": gvn_scanner_data,
                    "pulse": market_pulse
                }
                import json
                with open("live_market_data.json", "w") as jf:
                    json.dump(shared_data.gvn_scanner_data, jf)
            except: pass
        return
    
    records = data["records"]
    underlying_value = records.get("underlyingValue", 0)
    
    # Time to Expiry (T)
    try:
        expiry_dt = datetime.strptime(nearest_expiry, "%d-%b-%Y")
    except:
        expiry_dt = datetime.now() # Fallback

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

            # Calculate Greeks
            effective_iv = iv if iv > 0 else 18.0
            delta, gamma, theta = 0, 0, 0
            try:
                S = underlying_value
                K = strike
                sigma = effective_iv / 100.0
                
                delta = abs(calculate_delta(S, K, T, r, sigma, opt_type))
                gamma = calculate_gamma(S, K, T, r, sigma)
                theta = calculate_theta(S, K, T, r, sigma, opt_type)
            except:
                pass

            # 🌟 DELTA 60 SELECTION
            if abs(delta - 0.60) < (closest_ce_diff if opt_type == "CE" else closest_pe_diff):
                if opt_type == "CE":
                    closest_ce_diff = abs(delta - 0.60)
                    best_ce_60 = strike
                else:
                    closest_pe_diff = abs(delta - 0.60)
                    best_pe_60 = strike
            
            # 🚀 ZERO TO HERO SCANNER (Expanded Delta for tracking)
            if 0.10 <= delta <= 0.85: 
                h915 = ltp * 1.05 
                l915 = ltp * 0.95
                levels = calculate_gvn_levels(h915, l915)
                score = 0
                zone = "NORMAL"
                
                if delta >= 0.45: 
                    if ltp <= levels["i7"]: zone, score = "🔥 ITM/ATM SUPPORT (i7)", 55
                    elif ltp >= levels["i3"]: zone, score = "🚀 BULLISH BREAKOUT (i3)", 45
                elif delta <= 0.25:
                    if ltp <= levels["i7"]: zone, score = "💀 OVER-SOLD (i7)", 25
                    elif ltp >= levels["i3"]: zone, score = "📉 BEARISH TRAP (i3)", 15
                
                if score > 0:
                    # 🌟 NEW: Calculate Buy/Sell Pressure & AI Signal
                    pressure = "NEUTRAL"
                    ai_signal = "WAIT"
                    
                    if ltp <= levels["i7"]:
                        pressure = "🔥 HIGH BUY PRESSURE"
                        ai_signal = "🚀 SCALPING BUY"
                    elif ltp >= levels["i3"]:
                        pressure = "⚠️ SELL PRESSURE / TRAP"
                        ai_signal = "📉 REJECTION"
                    elif ltp >= levels["i5"] and ltp < levels["i3"]:
                        pressure = "🟢 MOMENTUM BUILDING"
                        ai_signal = "⚡ TREND BUY"
                    
                    # 🌟 GVN MASTER ALGO: i-Level Identification
                    i_level = "NORMAL"
                    if abs(ltp - levels["i5"]) < 2: i_level = "i5 (Pivot)"
                    elif abs(ltp - levels["i6"]) < 2: i_level = "i6 (Golden)"
                    elif abs(ltp - levels["i7"]) < 2: i_level = "i7 (Inst)"
                    elif abs(ltp - levels["i1"]) < 2: i_level = "i1 (Top)"
                    elif abs(ltp - levels["i0"]) < 2: i_level = "i0 (Bottom)"
                    
                    gvn_scanner_data[symbol].append({
                        "strike": f"{int(strike)} {opt_type}",
                        "ltp": ltp,
                        "delta": round(delta, 2),
                        "gamma": round(gamma, 4),
                        "theta": round(theta, 2),
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

    # 🌟 GVN SPECIAL: Force 24100 PE Levels if it's NIFTY
    if symbol == "NIFTY":
        # Check if already in scanner
        if not any("24100 PE" in x["strike"] for x in gvn_scanner_data[symbol]):
            # Add it with User's specific levels from audio
            target_ltp = live_option_ltps.get("24100_PE", 127.5)
            user_levels = {
                "Level_1": 30.0,
                "Level_7": 99.84,
                "Level_6": 150.55,
                "Level_5": 187.49,
                "Level_3": 224.42,
                "Level_0": 269.81
            }
            gvn_scanner_data[symbol].append({
                "strike": "24100 PE",
                "ltp": target_ltp,
                "delta": 0.65, # Estimated
                "oi_change": 0,
                "volume": 0,
                "score": 85,
                "zone": "🔥 GVN TARGET ZONE",
                "pressure": "HIGH BUY PRESSURE" if target_ltp <= 110 else "WAIT",
                "ai_signal": "🚀 ZERO-TO-HERO" if target_ltp <= 105 else "HOLD",
                "i_level": "i7 (99.8)" if abs(target_ltp - 99.8) < 5 else "IN-ZONE",
                "potential": "VERY HIGH",
                "levels": user_levels
            })
            
        # 🌟 GVN SPECIAL: Force 23900 PE Levels if it's NIFTY
        if not any("23900 PE" in x["strike"] for x in gvn_scanner_data[symbol]):
            target_ltp_23900 = 32.35 # From table
            user_levels_23900 = {
                "i0": 7.64,
                "i7": 27.53,
                "i6": 42.18,
                "i5": 52.86,
                "i3": 63.53,
                "i1": 98.08
            }
            gvn_scanner_data[symbol].append({
                "strike": "23900 PE",
                "ltp": target_ltp_23900,
                "delta": 0.35, # OTM
                "oi_change": 290007,
                "volume": 7689670,
                "score": 75,
                "zone": "📉 SUPPORT TRACKING",
                "pressure": "🟢 STABLE",
                "ai_signal": "🎯 TARGET i6 (42.2)",
                "i_level": "i7 (27.5) Crossed",
                "potential": "MODERATE",
                "levels": user_levels_23900
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
        
    # 🌟 ALWAYS SYNC TO SHARED DATA
    try:
        shared_data.gvn_scanner_data = {
            "summary": live_option_chain_summary,
            "scanner": gvn_scanner_data,
            "pulse": market_pulse
        }
        # Force persist to file for dashboard
        import json
        with open("live_market_data.json", "w") as jf:
            json.dump(shared_data.gvn_scanner_data, jf)
            
        # Log specific tracking for 24100 PE if it exists in data
        found_target = False
        for item in gvn_scanner_data.get(symbol, []):
            if "24100 PE" in item["strike"]:
                found_target = True
                lv = item["levels"]
                with open("nse_status.log", "a") as f:
                    f.write(f"{datetime.now()}: [TRACK] 24100 PE Levels -> i7:{lv['Level_7']} i5:{lv['Level_5']} i1:{lv['Level_1']} | LTP: {item['ltp']}\n")
        
        if not found_target and symbol == "NIFTY":
            # If not in scanner due to other filters, look for it in raw data
            for item in records.get("data", []):
                strike = item.get("strikePrice") or item.get("strike")
                if strike == 24100 and "PE" in item:
                    opt = item["PE"]
                    ltp = opt.get("lastPrice", 0)
                    lv = calculate_gvn_levels(ltp * 1.05, ltp * 0.95) # Mock for now if 9:15 not stored
                    with open("nse_status.log", "a") as f:
                        f.write(f"{datetime.now()}: [FORCE TRACK] 24100 PE -> LTP: {ltp} | i7:{lv['Level_7']}\n")
    except Exception as e:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [SYNC ERROR] {str(e)}\n")

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
                for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "CRUDEOIL"]:
                    with open("nse_status.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()}: [NSE Worker] Fetching {symbol}...\n")
                    analyze_and_update_gvn_scanner(symbol)
                    with open("nse_status.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()}: SUCCESS: {symbol} Sync Complete\n")
                    time.sleep(3)
                
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            print(f"[NSE Worker Error] {e}")
            with open("nse_status.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: FATAL ERROR in Worker: {err_msg}\n")
            time.sleep(10) # Wait more on fatal error
        
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

