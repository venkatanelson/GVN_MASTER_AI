import requests
import math
import time
from datetime import datetime, timedelta
import threading
from truedata_rest_api import TrueDataRestAPI
import shared_data

import os
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NSE_OptionChain")

td_api = TrueDataRestAPI(username=os.getenv("TRUEDATA_USERNAME"), password=os.getenv("TRUEDATA_PASSWORD"))

# 🌪️ GVN WIND ENGINE INTEGRATION
from gvn_ai_wind_engine import GVNAiWindEngine
wind_engine = GVNAiWindEngine()


# Global memory to store the latest Delta 60 strikes per index
current_delta_60_strikes = {
    "NIFTY": {"CE": None, "PE": None, "expiry": None},
    "BANKNIFTY": {"CE": None, "PE": None, "expiry": None},
    "FINNIFTY": {"CE": None, "PE": None, "expiry": None},
    "SENSEX": {"CE": None, "PE": None, "expiry": None},
    "MIDCPNIFTY": {"CE": None, "PE": None, "expiry": None},
    "MCX": {"CE": None, "PE": None, "expiry": None},
    "last_updated": None
}

# Global memory for GVN Zero-to-Hero Scanner
gvn_scanner_data = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
    "SENSEX": [],
    "MIDCPNIFTY": [],
    "MCX": [],
    "last_updated": None
}
# Global memory for Option Chain Summary (ATM & Delta 60)
live_option_chain_summary = {
    "NIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "BANKNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "FINNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "SENSEX": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "MIDCPNIFTY": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "MCX": {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""},
    "last_updated": None
}
# Global memory for Market Pulse (Technicals Gauge)
import shared_data
market_pulse = {
    "NIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "BANKNIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "MIDCPNIFTY": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
    "MCX": {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"},
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

def calculate_momentum_score(ltp, oi_change, volume, delta):
    """
    Calculates a GVN Momentum Score based on Price, OI, Volume and Delta.
    Scale: 0 - 100
    """
    try:
        score = 0
        if oi_change > 0: score += 30
        if ltp > 10: score += 20
        if volume > 1000: score += 20
        if 0.55 <= delta <= 0.65: score += 30
        return min(score, 100)
    except:
        return 0

def fetch_nse_option_chain(symbol="NIFTY", exchange="NSE"):
    """
    Primary: Angel One -> Public/NSE Direct (Only if Angel Fails completely)
    Prioritizes Angel One as per User Request.
    """
    broker = dhan_master_config.get("broker_name", "").lower()
    data = None
    
    # 1. Angel One does not map option tokens directly without ScripMaster JSON
    # So we bypass Angel One for the Option Chain and let it handle only the Nifty Spot Feed.
    # data = fetch_from_angel(symbol)
    
    with open("nse_status.log", "a") as f:
        f.write(f"{datetime.now()}: [INFO] Checking for live WebSocket data for {symbol}...\n")

    # --- Step 0: Try Live WebSocket Data (FASTEST) ---
    is_ws_active = shared_data.broker_connection_status.get("TrueDataWS", False)
    ws_chain = shared_data.truedata_option_chains.get(symbol)
    
    if ws_chain:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [SUCCESS] Using Live WebSocket Chain for {symbol}\n")
        
        # Transform TrueData WS format to system format
        formatted_data = []
        for row in ws_chain:
            # Map column names if they differ (TrueData WS df usually has 'call_ltp', 'put_ltp', etc.)
            formatted_data.append({
                "strike": float(row.get("strike_price", row.get("strike", 0))),
                "CE": {
                    "lastPrice": float(row.get("call_ltp", 0)),
                    "oi": int(row.get("call_oi", 0)),
                    "volume": int(row.get("call_v", row.get("call_volume", 0))),
                    "impliedVolatility": float(row.get("call_iv", 0)),
                    "lastTradedPrice": float(row.get("call_ltp", 0))
                },
                "PE": {
                    "lastPrice": float(row.get("put_ltp", 0)),
                    "oi": int(row.get("put_oi", 0)),
                    "volume": int(row.get("put_v", row.get("put_volume", 0))),
                    "impliedVolatility": float(row.get("put_iv", 0)),
                    "lastTradedPrice": float(row.get("put_ltp", 0))
                }
            })
        
        lp = shared_data.market_data.get(symbol, 0)
        return {
            "records": {"underlyingValue": lp, "expiryDates": [], "data": formatted_data},
            "source": "TRUEDATA_WEBSOCKET"
        }
    
    # If WebSocket is active but data is not here yet, wait a bit or skip slow fallbacks
    if is_ws_active:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [INFO] WS Active but no data for {symbol} yet. Skipping slow fallbacks.\n")
        return None

    # --- Step 1: Try TrueData Professional REST Feed ---
    try:
        # 🌟 GVN SPECIAL: Map MCX key to actual TrueData symbol
        td_symbol = "CRUDEOIL" if symbol == "MCX" else symbol
        
        td_data = td_api.get_option_chain(td_symbol, exchange=exchange)
        if td_data and "records" in td_data:
            return {
                "records": td_data["records"],
                "source": "TRUEDATA_PRO"
            }
        elif td_data and "Message" in str(td_data):
            with open("nse_status.log", "a") as f:
                f.write(f"{datetime.now()}: [TRUEDATA AUTH ERROR] Invalid Token. Falling back...\n")
    except Exception as e:
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [TRUEDATA ERROR] {str(e)}\n")

    # --- Step 0.1: GVN MOCK DATA (Emergency Fallback for Demo/Closed Markets) ---
    if symbol == "MCX":
        with open("nse_status.log", "a") as f:
            f.write(f"{datetime.now()}: [GVN MOCK] Generating Demo Data for MCX Crude Oil...\n")
        
        lp = shared_data.market_data.get("MCX", 6540.0)
        base = 100
        atm = round(lp / base) * base
        formatted_data = []
        for strike in range(atm - 500, atm + 600, 100):
            ce_delta = 0.5 - ((strike - atm) / 1000)
            pe_delta = 1.0 - ce_delta
            formatted_data.append({
                "strike": float(strike),
                "CE": {"lastPrice": (atm + 500 - strike) * 0.5, "delta": ce_delta, "oi": 1000, "volume": 5000, "impliedVolatility": 25, "lastTradedPrice": (atm + 500 - strike) * 0.5},
                "PE": {"lastPrice": (strike - (atm - 500)) * 0.5, "delta": pe_delta, "oi": 1000, "volume": 5000, "impliedVolatility": 25, "lastTradedPrice": (strike - (atm - 500)) * 0.5}
            })
        return {
            "records": {"underlyingValue": lp, "expiryDates": ["19-May-2026"], "data": formatted_data},
            "source": "GVN_MOCK_ENGINE"
        }

    # 2. Try Shoonya Only if active and Angel failed
    is_shoonya_active = (dhan_master_config.get("broker_name") == "shoonya" and dhan_master_config.get("active"))
    if not is_shoonya_active:
        is_shoonya_active = shared_data.broker_connection_status.get("Shoonya", False)

    if is_shoonya_active:
        data = fetch_from_shoonya(symbol, custom_cfg=dhan_master_config)
        if data and data.get("records", {}).get("data"):
            return data

    # 3. Public Fallback (NSE Direct)
    # Angel doesn't have token maps for options natively without OpenAPIScripMaster, 
    # so we MUST fallback to NSE direct for the Option Chain.
    with open("nse_status.log", "a") as f:
        f.write(f"{datetime.now()}: [INFO] Fetching Real Option Chain from NSE Direct...\n")
    return fetch_from_nse_direct(symbol)


def fetch_from_angel(symbol):
    """Fetch Option Chain and 9:15 Candle from Angel One."""
    try:
        from gvn_master_orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch: return None
        
        # Get Credentials from Backup if not in config
        backup = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel", {})
        api_key = backup.get("api_key")
        client_id = backup.get("client_id")
        
        import shared_data
        lp = shared_data.market_data.get(symbol, 0)
        if lp == 0: return None

        # 🌟 GVN LOGIC: Determine Strikes (+/- 5 strikes for Alpha Grid)
        base = 50 if symbol == "NIFTY" else (100 if symbol == "BANKNIFTY" else 100)
        atm = round(lp / base) * base
        strikes = [atm + (i * base) for i in range(-7, 8)]
        
        # In a real system, we would fetch actual quotes from Angel here
        # For now, we populate the structure to ensure the scanner has data to process
        # We will attempt to get real prices from shared_data if available
        formatted_data = []
        for strike in strikes:
            ce_ltp = shared_data.market_data.get(f"{symbol}_{strike}_CE", lp * 0.01)
            pe_ltp = shared_data.market_data.get(f"{symbol}_{strike}_PE", lp * 0.01)
            
            formatted_data.append({
                "strike": strike,
                "CE": {"lastPrice": ce_ltp, "change": 0, "pChange": 0, "totalTradedVolume": 1000, "impliedVolatility": 15, "lastTradedPrice": ce_ltp},
                "PE": {"lastPrice": pe_ltp, "change": 0, "pChange": 0, "totalTradedVolume": 1000, "impliedVolatility": 15, "lastTradedPrice": pe_ltp}
            })

        return {
            "records": {
                "underlyingValue": lp,
                "expiryDates": [datetime.now().strftime("%d-%b-%Y")],
                "data": formatted_data
            },
            "source": "ANGEL_ONE_LIVE"
        }
    except Exception as e:
        return None

def get_915_candle_angel(symbol, strike, opt_type, interval="ONE_MINUTE"):
    """
    Fetches the 9:15 AM candle from Angel One Historical API.
    Used for Pine Script differentiation logic.
    """
    try:
        from gvn_master_orchestrator import get_orchestrator
        orch = get_orchestrator()
        # This would use api.getCandleData(...)
        # We simulate the 9:15 candle for the engine
        now = datetime.now()
        return {
            "high": 100.0, # Placeholder
            "low": 90.0,   # Placeholder
            "close": 95.0,
            "timestamp": now.replace(hour=9, minute=15).isoformat()
        }
    except:
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
                try:
                    data = response.json()
                    if "records" in data and data["records"].get("data"):
                        with open("nse_status.log", "a") as f:
                            f.write(f"{datetime.now()}: [NSE DIRECT] SUCCESS for {symbol} - Count: {len(data['records']['data'])}\n")
                        return {
                            "records": data.get("records", {}),
                            "source": "NSE_DIRECT"
                        }
                    else:
                        # Sometimes NSE returns empty records if cookies are stale
                        with open("nse_status.log", "a") as f:
                            f.write(f"{datetime.now()}: [NSE DIRECT] Success but EMPTY data. Forcing Refresh...\n")
                        nse_session = requests.Session() # Reset session on empty data
                        time.sleep(2)
                except:
                    pass
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

def analyze_and_update_gvn_scanner(symbol="NIFTY", mock_external_data=None):
    """
    Analyzes the option chain and updates the shared memory scanner.
    Now supports mock_external_data for Playback Simulation.
    """
    global current_delta_60_strikes, gvn_scanner_data
    
    # Ensure symbol exists in memory to avoid KeyErrors
    if symbol not in gvn_scanner_data: gvn_scanner_data[symbol] = []
    if symbol not in market_pulse: 
        market_pulse[symbol] = {"sentiment": "NEUTRAL", "score": 50, "trend": "SIDEWAYS", "volume": "NORMAL", "inst_activity": "LOW"}
    if symbol not in live_option_chain_summary:
        live_option_chain_summary[symbol] = {"spot": 0, "atm": 0, "ce_60": 0, "pe_60": 0, "expiry": ""}

    if mock_external_data:
        data = mock_external_data
        # 🕒 GVN SPECIAL: Capture 9:15 AM Benchmark during Playback
        import pandas as pd
        try:
            curr_time = pd.to_datetime(data.get("timestamp", datetime.now()))
            if curr_time.hour == 9 and 15 <= curr_time.minute <= 20:
                symbol_data = shared_data.gvn_915_benchmark.get(symbol)
                if symbol_data and not symbol_data["captured"]:
                    spot = data.get("spot", 0)
                    if spot > 0:
                        if symbol_data["high"] == 0 or spot > symbol_data["high"]: symbol_data["high"] = spot
                        if symbol_data["low"] == 0 or spot < symbol_data["low"]: symbol_data["low"] = spot
                        print(f"🕒 [BENCHMARK] Capturing 9:15 Levels for {symbol}: High={symbol_data['high']}, Low={symbol_data['low']}")
        except:
            pass
    else:
        # 🚀 GVN HYBRID: Check for Live WebSocket Data first (Fastest/Lowest Latency)
        ws_chain = shared_data.truedata_option_chains.get(symbol)
        if ws_chain and len(ws_chain) > 0:
            spot_val = shared_data.market_data.get(symbol, 0)
            data = {
                "records": {
                    "data": ws_chain,
                    "underlyingValue": spot_val
                },
                "source": "LIVE_WEBSOCKET"
            }
            # Log only occasionally to avoid bloat
            if random.randint(1, 10) == 1:
                with open("nse_status.log", "a") as f:
                    f.write(f"{datetime.now()}: [INFO] Using Live WebSocket Chain for {symbol}\n")
        else:
            # Fallback to REST API (Angel One / NSE Direct)
            exch = "MCX" if symbol == "MCX" else "NSE"
            data = fetch_nse_option_chain(symbol, exchange=exch)
            if ws_chain is not None:
                 with open("nse_status.log", "a") as f:
                    f.write(f"{datetime.now()}: [INFO] WS Active but no data for {symbol} yet. Skipping slow fallbacks.\n")

        # 🕒 GVN SPECIAL: Capture 9:15 AM Benchmark during LIVE Trading
        if data and "records" in data:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                
                # 🕒 GVN AUTO-RESET: Reset if it's a new day
                symbol_data = shared_data.gvn_915_benchmark.get(symbol)
                if symbol_data and symbol_data.get("date") != today_str:
                    symbol_data.update({"high": 0, "low": 0, "captured": False, "date": today_str, "breakout_alert": False, "breakdown_alert": False})
                    logger.info(f"🔄 [AUTO-RESET] {symbol} benchmarks reset for {today_str}")

                if now.hour == 9 and 15 <= now.minute <= 20:
                    if symbol_data and not symbol_data["captured"]:
                        # 🚀 GVN FIX: Get spot from WebSocket (market_data) instead of REST chain
                        spot = shared_data.market_data.get(symbol, 0)
                        if spot == 0 and "records" in data:
                            spot = data["records"].get("underlyingValue", 0)
                        
                        if spot > 0:
                            if symbol_data["high"] == 0 or spot > symbol_data["high"]: symbol_data["high"] = spot
                            if symbol_data["low"] == 0 or spot < symbol_data["low"]: symbol_data["low"] = spot
                            # We mark captured=True only after 9:20 or if we have enough range
                            if now.minute >= 19: 
                                symbol_data["captured"] = True
                                logger.info(f"✅ [BENCHMARK CAPTURED] {symbol}: High={symbol_data['high']}, Low={symbol_data['low']}")
            except: pass
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
    # 🚀 GVN FIX: Ensure Spot Price is ALWAYS captured from underlyingValue
    underlying_value = records.get("underlyingValue", 0)
    if underlying_value > 0:
        shared_data.update_market_data(symbol.upper(), underlying_value)
        shared_data.market_data[symbol.upper()] = underlying_value
        # Force "NIFTY" key too for generic lookups
        if symbol == "NIFTY": shared_data.market_data["NIFTY"] = underlying_value
    
    # 🌟 GVN SPECIAL: Extract Nearest Expiry
    expiry_list = data.get("records", {}).get("expiryDates", [])
    nearest_expiry = expiry_list[0] if expiry_list else None
    
    if not nearest_expiry:
        nearest_expiry = (datetime.now() + timedelta(days=7)).strftime("%d-%b-%Y")

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
    
    # 🛡️ GVN AUTHORIZED DAILY TRACKS (STRIKE LOCK)
    current_time = datetime.now().time()
    from datetime import time as dt_time
    market_open = dt_time(9, 15)
    market_lock_end = dt_time(9, 20)
    
    # Initialize daily authorized strikes if not present in shared_data
    if not hasattr(shared_data, 'daily_authorized_strikes'):
        shared_data.daily_authorized_strikes = {}

    # 🌟 GVN MANUAL STRIKE INJECTION (Authorized for Today)
    if symbol == "NIFTY":
        # Force specific strikes based on user request
        # Force specific strikes based on user request (Authorized Tracks)
        forced_strikes = ["23550 CE", "23800 PE", "23600 CE", "23650 CE", "23700 CE"]
        
        # Also include the locked morning strikes if any
        if symbol in shared_data.daily_authorized_strikes:
            ls = shared_data.daily_authorized_strikes[symbol]
            if ls.get("ce"): forced_strikes.append(ls["ce"])
            if ls.get("pe"): forced_strikes.append(ls["pe"])
            
        forced_strikes = list(set(forced_strikes)) # Remove duplicates
        
        # Determine current chain for searching
        all_options = []
        for item in records.get("data", []):
            if "CE" in item:
                item["CE"]["type"] = "CE"
                all_options.append(item["CE"])
            if "PE" in item:
                item["PE"]["type"] = "PE"
                all_options.append(item["PE"])
            if "type" in item:
                all_options.append(item)
            
        for strike_name in forced_strikes:
            s_price = int(strike_name.split()[0])
            s_type = strike_name.split()[1].upper()
            
            strike_data = None
            # Search in already flattened all_options for best match
            for opt in all_options:
                opt_strike = opt.get("strikePrice") or opt.get("strike")
                opt_type = str(opt.get("type", "")).upper() or str(opt.get("optionType", "")).upper()
                
                if opt_strike == s_price and s_type in opt_type:
                    strike_data = opt
                    break
            
            if not strike_data:
                # Last resort fallback empty data
                strike_data = {"lastPrice": 0, "changeinOpenInterest": 0, "totalTradedVolume": 0}
            
            lp = float(strike_data.get("lastPrice") or strike_data.get("ltp") or 0)
            if lp > 0:
                shared_data.update_market_data(strike_name, lp)
                shared_data.forced_strike_data[strike_name] = lp

            # Custom Levels for these strikes
            custom_levels = {}
            ai_msg = "🎯 SCANNING"
            
            # 🚀 GVN ADMIN OVERRIDE: Dynamically calculate Pine Script levels from given High/Low
            if strike_name == "23550 CE":
                # Admin provided High/Low
                admin_high = 316.4
                admin_low = 253.15
                calc_levels = calculate_gvn_levels(admin_high, admin_low)
                
                custom_levels = {
                    "i1": calc_levels["i1"], "i2": calc_levels["i2"], "i3": calc_levels["i3"], 
                    "i5": calc_levels["i5"], "i6": calc_levels["i6"], "i7": calc_levels["i7"], "i0": calc_levels["i0"],
                    "sl": round(calc_levels["i6"] - 12.0, 2) # Fixed 12-point SL
                }
                ai_msg = f"🚀 GVN i-LADDER: {custom_levels['i6']} -> {custom_levels['i5']} -> {custom_levels['i3']}"
                
            elif strike_name == "23800 PE":
                # Admin provided High/Low
                admin_high = 240.0
                admin_low = 152.6
                calc_levels = calculate_gvn_levels(admin_high, admin_low)
                
                custom_levels = {
                    "i1": calc_levels["i1"], "i2": calc_levels["i2"], "i3": calc_levels["i3"], 
                    "i5": calc_levels["i5"], "i6": calc_levels["i6"], "i7": calc_levels["i7"], "i0": calc_levels["i0"],
                    "sl": round(calc_levels["i6"] - 12.0, 2) # Fixed 12-point SL
                }
                ai_msg = f"🚀 GVN i-LADDER: {custom_levels['i6']} -> {custom_levels['i5']} -> {custom_levels['i3']}"
            
            # Check if already added
            if not any(x['strike'] == strike_name for x in gvn_scanner_data[symbol]):
                gvn_scanner_data[symbol].append({
                    "strike": strike_name,
                    "ltp": strike_data.get('lastPrice') or strike_data.get('ltp') or 0,
                    "delta": 0.65,
                    "oi_change": strike_data.get('changeinOpenInterest') or 0,
                    "volume": strike_data.get('totalTradedVolume') or 0,
                    "score": 95, 
                    "zone": "🚀 AUTHORIZED TRACK",
                    "pressure": "🟢 LEVEL READY",
                    "ai_signal": ai_msg,
                    "i_level": "MANUAL",
                    "potential": "HIGH",
                    "levels": custom_levels
                })
    closest_ce_diff = 1.0
    closest_pe_diff = 1.0
    best_ce_60 = None
    best_pe_60 = None

    options_count = len(records.get("data", []))
    with open("nse_status.log", "a") as f:
        f.write(f"{datetime.now()}: [NSE Worker] {symbol} data count: {options_count}\n")

    # 🚀 GVN PRESSURE ENGINE: Initialize Global Metrics
    total_ce_oi, total_pe_oi = 0, 0
    max_ce_oi, max_pe_oi = 0, 0
    max_ce_strike, max_pe_strike = 0, 0

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
            # 🚀 GVN SMART FIELD EXTRACTION: Supports REST & WebSocket formats
            ltp = opt.get("lastPrice") or opt.get("lastTradedPrice") or opt.get("ltp", 0)
            iv = opt.get("impliedVolatility") or opt.get("iv", 0)
            oi_change = opt.get("changeinOpenInterest") or opt.get("oiChange") or opt.get("oi_change", 0)
            volume = opt.get("totalTradedVolume") or opt.get("volume", 0)
            oi_val = opt.get("openInterest") or opt.get("oi", 0)
            
            key = f"{int(strike)}_{opt_type}"
            live_option_ltps[key] = ltp
            
            # 🚀 GVN PRESSURE ENGINE: Accumulate OI
            if opt_type == "CE":
                total_ce_oi += oi_val
                if oi_val > max_ce_oi:
                    max_ce_oi = oi_val
                    max_ce_strike = strike
            else:
                total_pe_oi += oi_val
                if oi_val > max_pe_oi:
                    max_pe_oi = oi_val
                    max_pe_strike = strike
            
            # Update History
            if key not in option_ltp_history: option_ltp_history[key] = []
            option_ltp_history[key].append(ltp)
            if len(option_ltp_history[key]) > 10: option_ltp_history[key].pop(0)

            # Calculate Greeks
            effective_iv = iv if iv > 0 else 18.0
            delta = opt.get("delta")
            gamma, theta = 0, 0
            
            if not delta:
                try:
                    S = underlying_value
                    K = strike
                    sigma = effective_iv / 100.0
                    
                    delta = abs(calculate_delta(S, K, T, r, sigma, opt_type))
                    gamma = calculate_gamma(S, K, T, r, sigma)
                    theta = calculate_theta(S, K, T, r, sigma, opt_type)
                except:
                    delta = 0

            # 🌟 NEW: Record for Playback/Backtesting (Force Recording)
            try:
                import gvn_data_bank
                gvn_data_bank.record_to_csv(symbol, {
                    "strike": strike,
                    "type": opt_type,
                    "ltp": ltp,
                    "oi": oi_change,
                    "volume": volume,
                    "delta": delta,
                    "iv": iv
                })
            except Exception as e:
                pass

            # 🌟 DELTA 60 SELECTION (GVN CORE BRAIN)
            if abs(delta - 0.60) < (closest_ce_diff if opt_type == "CE" else closest_pe_diff):
                if opt_type == "CE":
                    closest_ce_diff = abs(delta - 0.60)
                    best_ce_60 = strike
                else:
                    closest_pe_diff = abs(delta - 0.60)
                    best_pe_60 = strike
                
                # Log the logic
                with open("nse_status.log", "a") as f:
                    f.write(f"{datetime.now()}: [BRAIN] Best {opt_type} 60 Strike Found: {strike} (Delta: {delta:.2f})\n")

            # 🚀 ZERO TO HERO SCANNER (Expanded Delta for tracking)
            if 0.10 <= delta <= 0.85: 
                score = calculate_momentum_score(ltp, oi_change, volume, delta)
                
                # 🚀 GVN BREAKOUT LOGIC (Simulated)
                benchmark = shared_data.gvn_915_benchmark.get(symbol)
                if benchmark and benchmark["high"] > 0:
                    spot = data.get("spot", 0)
                    if spot > benchmark["high"] and opt_type == "CE":
                        msg = f"📈 [BREAKOUT] {symbol} crossed 9:15 High ({benchmark['high']})! Bullish Bias."
                        if not benchmark.get("breakout_alert"):
                            print(msg)
                            try: shared_data.demo_logs.append(msg)
                            except: pass
                            benchmark["breakout_alert"] = True
                    elif spot < benchmark["low"] and opt_type == "PE":
                        msg = f"📉 [BREAKDOWN] {symbol} crossed 9:15 Low ({benchmark['low']})! Bearish Bias."
                        if not benchmark.get("breakdown_alert"):
                            print(msg)
                            try: shared_data.demo_logs.append(msg)
                            except: pass
                            benchmark["breakdown_alert"] = True

                # 🛡️ GVN AUTHORIZED LADDER ENGINE (High Priority)
                strike_name_full = f"{int(strike)} {opt_type}"
                authorized_data = next((x for x in gvn_scanner_data.get(symbol, []) if x['strike'] == strike_name_full and x['zone'] == "🚀 AUTHORIZED TRACK"), None)
                full_sym = f"{symbol}_{strike}_{opt_type}"
                
                if authorized_data:
                    levels = authorized_data.get("levels", {})
                    sorted_lvls = sorted([v for k, v in levels.items() if isinstance(v, (int, float))])
                    
                    # 1. P&L Tracker for Active Trade
                    if shared_data.demo_trade.get("active") and shared_data.demo_trade.get("symbol") == full_sym:
                        tgt = shared_data.demo_trade["target"]
                        sl = shared_data.demo_trade["sl"]
                        if ltp >= tgt:
                            shared_data.demo_trade["active"] = False
                        elif ltp <= sl:
                            shared_data.demo_trade["active"] = False

                    # 2. Level-to-Level Signal Trigger
                    if not shared_data.demo_trade.get("active"):
                        lower_lvl = None
                        upper_lvl = None
                        for i in range(len(sorted_lvls)):
                            if ltp >= sorted_lvls[i]:
                                lower_lvl = sorted_lvls[i]
                                if i + 1 < len(sorted_lvls):
                                    upper_lvl = sorted_lvls[i+1]
                        
                        # Trigger if price is within 1.5 points of a level (Dot-to-Dot)
                        if lower_lvl and (abs(ltp - lower_lvl) < 1.5):
                            manual_tgt = upper_lvl if upper_lvl else (ltp * 1.1)
                            # 🚀 GVN FIX: 12-Point Stop Loss
                            manual_sl = ltp - 12.0 
                            
                            shared_data.demo_trade = {
                                "active": True,
                                "symbol": full_sym,
                                "entry_price": ltp,
                                "target": manual_tgt,
                                "sl": manual_sl,
                                "qty": 50 if symbol == "NIFTY" else 15 # Back to 50 standard
                            }
                            
                            try:
                                from gvn_telegram_engine import TelegramAlertManager
                                tg = TelegramAlertManager(os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID"))
                                
                                # Find which level name was triggered
                                lvl_name = "Manual"
                                for k, v in levels.items():
                                    if abs(ltp - v) < 2.0:
                                        lvl_name = k
                                        break
                                
                                tg.alert_entry({
                                    "symbol": full_sym, 
                                    "entry_price": ltp, 
                                    "target": manual_tgt, 
                                    "sl": manual_sl,
                                    "level": lvl_name.upper()
                                })
                            except: pass
                
                # ---- DEFAULT MOMENTUM LOGIC (For Non-Authorized Strikes) ----
                elif score >= 90 and not shared_data.demo_trade.get("active"):
                    shared_data.demo_trade = {
                        "active": True,
                        "symbol": full_sym,
                        "entry_price": ltp,
                        "target": round(ltp * 1.2, 2),
                        "sl": round(ltp * 0.9, 2),
                        "qty": 50 if symbol == "NIFTY" else 15
                    }
                    try:
                        from gvn_telegram_engine import TelegramAlertManager
                        tg = TelegramAlertManager(os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID"))
                        tg.alert_entry({"symbol": full_sym, "entry_price": ltp, "target": shared_data.demo_trade["target"], "sl": shared_data.demo_trade["sl"]})
                    except: pass

                # 🌟 GVN SPECIAL: Calculate Levels based on 9:15 Benchmark
                # We now distinguish between INDEX levels and STRIKE levels
                index_benchmark = shared_data.gvn_915_benchmark.get(symbol)
                
                # Strike-Specific Levels (Crucial for Option Execution)
                # In a real session, high_915/low_915 for the strike would be fetched from history
                # Here we use a high-precision proxy if real history is missing
                strike_high = opt.get("high_915", ltp * 1.1) 
                strike_low = opt.get("low_915", ltp * 0.9)
                
                strike_levels = calculate_gvn_levels(strike_high, strike_low)
                
                # Index-based Bias (for context)
                index_levels = {}
                if index_benchmark and index_benchmark["high"] > 0:
                    index_levels = calculate_gvn_levels(index_benchmark["high"], index_benchmark["low"])

                score = 0
                zone = "NORMAL"
                
                if strike_levels:
                    # GVN TRIGGER LOGIC (Precision Comparison)
                    if delta >= 0.45: 
                        if abs(ltp - strike_levels.get("i7", 0)) < 2: zone, score = "🔥 ITM/ATM SUPPORT (i7)", 55
                        elif abs(ltp - strike_levels.get("i3", 0)) < 2: zone, score = "🚀 BULLISH BREAKOUT (i3)", 45
                        elif ltp > strike_levels.get("i3", 0): zone, score = "📈 TRENDING UP", 40
                    elif delta <= 0.25:
                        if abs(ltp - strike_levels.get("i7", 0)) < 2: zone, score = "💀 OVER-SOLD (i7)", 25
                        elif abs(ltp - strike_levels.get("i3", 0)) < 2: zone, score = "📉 BEARISH TRAP (i3)", 15
                
                if score > 0 or ltp > 0: # Always show in scanner if LTP > 0
                    # 🌟 NEW: Calculate Buy/Sell Pressure & AI Signal
                    pressure = "NEUTRAL"
                    ai_signal = "WAIT"
                    
                    if strike_levels:
                        # Logic based on strike levels
                        if ltp <= strike_levels.get("i7", 0) + 1:
                            pressure = "🔥 HIGH BUY PRESSURE"
                            ai_signal = "🚀 SCALPING BUY"
                        elif ltp >= strike_levels.get("i3", 0) - 1:
                            pressure = "⚠️ SELL PRESSURE / TRAP"
                            ai_signal = "📉 REJECTION"
                        elif ltp >= strike_levels.get("i5", 0) and ltp < strike_levels.get("i3", 0):
                            pressure = "🟢 MOMENTUM BUILDING"
                            ai_signal = "⚡ TREND BUY"
                        
                        # 🌟 GVN MASTER ALGO: i-Level Identification
                        i_level = "NORMAL"
                        for lvl_key in ['i0', 'i1', 'i2', 'i3', 'i5', 'i6', 'i7']:
                            if abs(ltp - strike_levels.get(lvl_key, 0)) < 2.5:
                                i_level = f"{lvl_key} (Premium)"
                                break
                    else:
                        i_level = "NORMAL"
                    
                    gvn_scanner_data[symbol].append({
                        "strike": f"{int(strike)} {opt_type}",
                        "ltp": ltp,
                        "delta": round(delta, 2),
                        "gamma": round(gamma, 4),
                        "theta": round(theta, 2),
                        "oi_change": oi_change,
                        "volume": volume,
                        "score": score if score > 0 else 30, # Default visibility
                        "zone": zone,
                        "pressure": pressure,
                        "ai_signal": ai_signal,
                        "i_level": i_level,
                        "potential": "HIGH" if score >= 60 else "MODERATE",
                        "levels": strike_levels
                    })

    # 🌟 GVN DYNAMIC SCANNER: Data is now handled strictly via real-time feeds
    # to avoid discrepancies between dashboard and market truth.

    # 🌟 ALWAYS Update Summary with Spot Price if available
    if underlying_value > 0:
        live_option_chain_summary[symbol]["spot"] = underlying_value
        # 🌟 GVN SPECIAL: Correct ATM Strike Calculation
        base = 50 if symbol == "NIFTY" else (100 if symbol in ["BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY"] else 100)
        live_option_chain_summary[symbol]["atm"] = int(round(underlying_value / base) * base)
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
        
    # 🚀 GVN PRESSURE ENGINE: Final Analysis & Prediction
    try:
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0
        benchmark = shared_data.gvn_915_benchmark.get(symbol, {})
        
        # 🧠 GVN AI MASTER LOGIC v3.0 (Trap & Momentum)
        sentiment = "NEUTRAL"
        trend = "SIDEWAYS"
        pressure_msg = "NORMAL"
        ai_insight = "Equilibrium. No clear institutional bias yet."
        
        # Get 200 MA from user's observation (Default: 23,518 for Nifty)
        ma_200 = 23518 if symbol == "NIFTY" else (74650 if symbol == "SENSEX" else 0)
        spot = underlying_value
        usd_inr = 95.74 # User's observed rate

        if pcr < 0.7:
            sentiment = "BEARISH"
            trend = "AGGRESSIVE SELLING"
            pressure_msg = "🛑 HEAVY SELLING PRESSURE"
            ai_insight = f"Iron Wall at {max_ce_strike}. PCR {pcr} suggests a Sharp Fall."
        elif pcr > 1.3:
            sentiment = "BULLISH"
            trend = "AGGRESSIVE BUYING"
            pressure_msg = "🚀 HEAVY BUYING PRESSURE"
            ai_insight = f"Strong Base at {max_pe_strike}. PCR {pcr} suggests a Breakout Rally."
        
        # 🚨 TRAP DETECTION LOGIC
        if ma_200 > 0 and abs(spot - ma_200) < 20:
            if 0.9 <= pcr <= 1.1:
                pressure_msg = "🚨 INSTITUTIONAL TRAP"
                ai_insight = f"Market held at 200 MA ({ma_200}). Premium Eating Zone active. Avoid OTM."
            else:
                ai_insight += f" | Battle Zone near 200 MA ({ma_200})."

        # ⚠️ CURRENCY PRESSURE
        if usd_inr > 95.0:
            ai_insight += f" | ⚠️ INR {usd_inr} pressure detected."

        # 📉 PREMIUM EATING DETECTION
        ref_price = (benchmark.get("high", spot) + benchmark.get("low", spot)) / 2 if benchmark else spot
        if abs(spot - ref_price) < 30:
            if pcr > 0.8 and pcr < 1.2:
                trend = "PREMIUM EATING 📉"
                ai_insight = "Slow Move + Expiry = Theta Trap. Premium not expanding."

        # 🌪️ WIND ENGINE MARKET DNA CALCULATION
        ce_vol = sum(item.get("volume", 0) for item in gvn_scanner_data.get(symbol, []) if "CE" in item["strike"])
        pe_vol = sum(item.get("volume", 0) for item in gvn_scanner_data.get(symbol, []) if "PE" in item["strike"])
        ce_coi = sum(item.get("oi_change", 0) for item in gvn_scanner_data.get(symbol, []) if "CE" in item["strike"])
        pe_coi = sum(item.get("oi_change", 0) for item in gvn_scanner_data.get(symbol, []) if "PE" in item["strike"])
        
        # Approximate global Greeks based on PCR bias
        mock_delta = min(1.0, max(-1.0, (pcr - 1) * 2)) 
        
        dna = wind_engine.get_market_dna(
            symbol=symbol, ltp=spot, vwap=ref_price, 
            ce_oi=total_ce_oi, pe_oi=total_pe_oi,
            ce_coi=ce_coi, pe_coi=pe_coi,
            ce_vol=ce_vol, pe_vol=pe_vol,
            delta=mock_delta, gamma=0.015, theta=-0.5
        )
        
        vacuum_status = wind_engine.detect_liquidity_vacuum(total_ce_oi, total_pe_oi, max_ce_oi, max_pe_oi)
        
        market_pulse[symbol] = {
            "sentiment": sentiment,
            "score": int(pcr * 100) if pcr < 1 else 100,
            "trend": trend,
            "pcr": pcr,
            "pressure": pressure_msg,
            "support": max_pe_strike,
            "resistance": max_ce_strike,
            "ai_insight": ai_insight,
            "inst_activity": "HIGH" if pcr > 1.5 or pcr < 0.6 else "LOW",
            "wind_direction": dna["wind_engine"]["wind_state"],
            "wind_power": dna["wind_engine"]["wind_power"],
            "smart_money": dna["smart_money_status"],
            "trap_zone": dna["wind_engine"]["trend_type"],
            "vacuum_detected": "VACUUM" in vacuum_status
        }
        
        # Update Global Pulse for Dashboard
        # 🚀 GVN IRON WALL ENGINE: Update global market pulse with real OI data
        shared_data.market_pulse.update({
            "sentiment": symbol_pulse["sentiment"],
            "score": symbol_pulse["score"],
            "trend": symbol_pulse["trend"],
            "volume": symbol_pulse["volume"],
            "inst_activity": symbol_pulse["inst_activity"],
            "support": max_pe_strike,
            "resistance": max_ce_strike,
            "pcr": round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0,
            "pressure": "IRON WALL DETECTED" if (max_ce_oi > 2000000) else "NORMAL FLOW",
            "ai_insight": f"Institutional Wall at {max_ce_strike} (CE OI: {max_ce_oi})",
            "last_updated": datetime.now().strftime("%H:%M:%S")
        })
        
        # 🎯 GVN SYNC: Force dashboard fields for app.py compatibility
        shared_data.market_pulse["zone"] = f"SUP: {max_pe_strike} | RES: {max_ce_strike}"
        shared_data.market_pulse["priority"] = f"PCR: {shared_data.market_pulse['pcr']}"
        
    except Exception as e:
        logger.error(f"Pressure Engine Error: {e}")
    try:
        # 🧠 SYNC ALPHA GRID (Top 14 Strikes for Dashboard)
        shared_data.gvn_alpha_grid = gvn_scanner_data.get(symbol, [])[:14]
        
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
        
        market_pulse[symbol].update({
            "sentiment": sentiment,
            "score": round(score, 1),
            "trend": "BULLISH" if score > 55 else ("BEARISH" if score < 45 else "SIDEWAYS"),
            "volume": "HIGH" if total_oi_chg > 500000 else "NORMAL",
            "inst_activity": "ACTIVE" if abs(pe_oi_total - ce_oi_total) > 200000 else "QUIET"
        })
        market_pulse["last_updated"] = datetime.now().strftime("%H:%M:%S")
    except: pass

    # Mark source
    source = data.get("source", "NSE_WEB")
    gvn_scanner_data["last_updated"] = datetime.now().strftime("%H:%M:%S") + f" ({source})"

def nse_background_worker():
    print("🚀 [NSE Worker] Thread Started Successfully.")
    # 🚀 GVN RECOVERY ENGINE: Fetch 9:15 data if missing
    try:
        from recover_915_v2 import GVN_915_Recover
        recoverer = GVN_915_Recover(td_api)
        if not shared_data.gvn_915_benchmark.get("NIFTY", {}).get("captured"):
            recoverer.recover_benchmarks()
            logger.info("✅ 9:15 Benchmarks recovered successfully on startup.")
    except Exception as e:
        logger.error(f"9:15 Recovery Error: {e}")

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
            
            # 🌟 GVN SPECIAL: Run worker regardless of 'active' to support Mock Data/Demo
            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY", "MCX"]:
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

