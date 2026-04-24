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
# Global memory for full Option Chain data
full_option_chain_data = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
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

def fetch_option_chain(symbol="NIFTY"):
    """
    Directly uses Dhan API for fetching real-time Option Chain data.
    """
    if not dhan_master_config["active"] or not dhan_master_config["access_token"]:
        return None
        
    from dhanhq import dhanhq
    try:
        dhan = dhanhq(dhan_master_config["client_id"], dhan_master_config["access_token"])
        
        # Security IDs for Indices in Dhan
        sec_ids = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27", "SENSEX": "1"}
        sid = sec_ids.get(symbol)
        if not sid: return None
        
        # 🌟 SMART SEGMENT DETECTION
        if symbol == "SENSEX":
            idx_segment = "BSE_INDEX" # Often used for Sensex in Dhan
        else:
            idx_segment = "IDX_I"
            
        # Get LTP first using quote_data
        instruments = {idx_segment: [sid]}
        lp_resp = dhan.quote_data(instruments)
        lp = lp_resp.get('data', {}).get(sid, {}).get('lastPrice', 0)
        
        # Get Option Chain from Dhan
        try:
            # 🌟 NEW: Try to get expiry list
            expiry_resp = dhan.expiry_list(sid, idx_segment)
            
            with open("dhan_feed_status.log", "a") as f:
                f.write(f"{datetime.now()}: [DHAN EXPIRY DEBUG] {symbol} Resp: {expiry_resp}\n")
            
            nearest_expiry = ""
            if expiry_resp.get('status') == 'success' and expiry_resp.get('data'):
                nearest_expiry = expiry_resp.get('data')[0]
                
            # 🌟 FALLBACK: If expiry_list fails, calculate next Thursday
            if not nearest_expiry:
                from datetime import date, timedelta
                d = date.today()
                while d.weekday() != 3: # Thursday
                    d += timedelta(1)
                nearest_expiry = d.strftime("%Y-%m-%d")
                
            # Now fetch the actual option chain for this expiry
            chain_resp = dhan.option_chain(sid, idx_segment, nearest_expiry)
            
            with open("dhan_feed_status.log", "a") as f:
                f.write(f"{datetime.now()}: [DHAN DEBUG] {symbol} (Expiry: {nearest_expiry}) Option Chain Status: {chain_resp.get('status')} | Remarks: {chain_resp.get('remarks')}\n")
            
            if chain_resp.get('status') == 'success':
                chain_data = chain_resp.get('data', [])
                return {
                    "records": {
                        "underlyingValue": lp,
                        "expiryDates": expiry_resp.get('data', [datetime.now().strftime("%Y-%m-%d")]), 
                        "data": chain_data
                    },
                    "source": "DHAN_OPTION_CHAIN",
                    "nearest_expiry": nearest_expiry
                }
        except Exception as e:
            with open("dhan_feed_status.log", "a") as f:
                f.write(f"{datetime.now()}: [DHAN DEBUG ERROR] {symbol}: {str(e)}\n")

        return {
            "records": {
                "underlyingValue": lp,
                "expiryDates": [datetime.now().strftime("%Y-%m-%d")], 
                "data": [] # Still return index price at least
            },
            "source": "DHAN_LTP_ONLY"
        }
    except Exception as e:
        with open("dhan_feed_status.log", "a") as f:
            f.write(f"{datetime.now()}: [DHAN ERROR] {str(e)}\n")
    return None

def analyze_and_update_gvn_scanner(symbol="NIFTY"):
    global current_delta_60_strikes, gvn_scanner_data
    
    data = fetch_option_chain(symbol)
    if not data or "records" not in data: 
        return
        
    records = data["records"]
    underlying_value = records.get("underlyingValue", 0)
    expiry_dates = records.get("expiryDates", [])
    if not expiry_dates: return
    nearest_expiry = expiry_dates[0]
    
    # Time to Expiry (T)
    try:
        expiry_dt = datetime.strptime(nearest_expiry, "%d-%b-%Y")
    except ValueError:
        try:
            expiry_dt = datetime.strptime(nearest_expiry, "%Y-%m-%d")
        except ValueError:
            expiry_dt = datetime.now() + timedelta(days=1)
    
    now_dt = datetime.now()
    days_to_expiry = max((expiry_dt - now_dt).days, 0.01)
    T = days_to_expiry / 365.0  
    r = 0.07 

    # Reset scanner data for this symbol
    gvn_scanner_data[symbol] = []
    chain_map = {} # To store strike-wise CE and PE data
    
    best_ce_60 = None
    best_pe_60 = None
    closest_ce_diff = 1.0
    closest_pe_diff = 1.0

    options_count = len(records.get("data", []))
    with open("dhan_feed_status.log", "a") as f:
        f.write(f"{datetime.now()}: [Dhan Worker] {symbol} data count: {options_count}\n")

    for item in records.get("data", []):
        strike = item.get("strikePrice") or item.get("strike")
        if not strike: continue
        
        options_to_process = []
        if "CE" in item or "PE" in item:
            if "CE" in item: options_to_process.append(("CE", item["CE"]))
            if "PE" in item: options_to_process.append(("PE", item["PE"]))
        elif "type" in item:
            opt_type = item.get("type") # "CE" or "PE"
            options_to_process.append((opt_type, item))
            
        for opt_type, opt in options_to_process:
            ltp = opt.get("lastPrice") or opt.get("lastTradedPrice", 0)
            iv = opt.get("impliedVolatility", 0)
            oi = opt.get("openInterest") or opt.get("oi", 0)
            oi_change = opt.get("changeinOpenInterest") or opt.get("oiChange", 0)
            volume = opt.get("totalTradedVolume") or opt.get("volume", 0)
            
            # Store in chain_map
            if strike not in chain_map:
                chain_map[strike] = {"strike": strike}
            
            suffix = opt_type.lower()
            chain_map[strike].update({
                f"{suffix}_ltp": ltp,
                f"{suffix}_oi": oi,
                f"{suffix}_iv": round(iv, 2),
                f"{suffix}_vol": volume
            })

            key = f"{int(strike)}_{opt_type}"
            live_option_ltps[key] = ltp
            
            if key not in option_ltp_history: option_ltp_history[key] = []
            option_ltp_history[key].append(ltp)
            if len(option_ltp_history[key]) > 10: option_ltp_history[key].pop(0)

            effective_iv = iv if iv > 0 else 18.0
            delta = 0
            try:
                delta = abs(calculate_delta(underlying_value, strike, T, r, effective_iv/100.0, opt_type))
            except:
                delta = 0

            # DELTA 60 SELECTION
            if abs(delta - 0.60) < (closest_ce_diff if opt_type == "CE" else closest_pe_diff):
                if opt_type == "CE":
                    closest_ce_diff = abs(delta - 0.60)
                    best_ce_60 = strike
                else:
                    closest_pe_diff = abs(delta - 0.60)
                    best_pe_60 = strike
            
            # ZERO TO HERO SCANNER
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

    if underlying_value > 0:
        live_option_chain_summary[symbol]["spot"] = underlying_value
        atm = int(round(underlying_value / (50 if symbol == "NIFTY" else 100)) * (50 if symbol == "NIFTY" else 100))
        live_option_chain_summary[symbol]["atm"] = atm
        live_option_chain_summary["last_updated"] = datetime.now().strftime("%H:%M:%S")

        # 🌟 Store Full Option Chain
        sorted_chain = sorted(chain_map.values(), key=lambda x: x['strike'])
        # Mark ATM row
        for row in sorted_chain:
            row['is_atm'] = (row['strike'] == atm)
        
        full_option_chain_data[symbol] = sorted_chain
        full_option_chain_data["last_updated"] = datetime.now().strftime("%H:%M:%S")

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
        
        try:
            import json
            with open("live_market_data.json", "w") as jf:
                json.dump(live_option_chain_summary, jf)
        except: pass

    gvn_scanner_data[symbol] = sorted(gvn_scanner_data[symbol], key=lambda x: x["score"], reverse=True)[:10]
    
    try:
        ce_oi_total = sum(item.get('oi_change', 0) for item in gvn_scanner_data[symbol] if 'CE' in item['strike'])
        pe_oi_total = sum(item.get('oi_change', 0) for item in gvn_scanner_data[symbol] if 'PE' in item['strike'])
        
        total_oi_chg = abs(ce_oi_total) + abs(pe_oi_total)
        score = 50
        if total_oi_chg > 0:
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

    source = data.get("source", "DHAN_API")
    gvn_scanner_data["last_updated"] = datetime.now().strftime("%H:%M:%S") + f" ({source})"

def live_feed_background_worker():
    print("🚀 [Dhan API Live Feed Worker] Thread Started Successfully.")
    while True:
        try:
            if not dhan_master_config.get('active'):
                try:
                    import sqlite3
                    conn = sqlite3.connect('instance/gvn_algo_pro.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT client_id, encrypted_access_token FROM user_broker_config LIMIT 1")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        from cryptography.fernet import Fernet
                        cipher = Fernet(b'gvn_secure_key_for_encryption_26')
                        token = cipher.decrypt(row[1]).decode()
                        
                        dhan_master_config.update({
                            "client_id": row[0],
                            "access_token": token,
                            "active": True
                        })
                        with open("dhan_feed_status.log", "a", encoding="utf-8") as f:
                            f.write(f"{datetime.now()}: [AUTO-SYNC] Dhan Keys Loaded from DB.\n")
                    conn.close()
                except: pass

            with open("dhan_feed_status.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: Dhan Worker Pulse... (Active: {dhan_master_config.get('active')})\n")
            
            if dhan_master_config.get('active'):
                for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]:
                    with open("dhan_feed_status.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()}: [Dhan Worker] Fetching {symbol}...\n")
                    analyze_and_update_gvn_scanner(symbol)
                    with open("dhan_feed_status.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()}: SUCCESS: {symbol} Sync Complete\n")
                    time.sleep(3)
                
        except Exception as e:
            print(f"[Dhan Worker Error] {e}")
            with open("dhan_feed_status.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: FATAL ERROR: {str(e)}\n")
        
        time.sleep(15)

def start_live_feed_worker():
    print("\n" + "="*50)
    print("🔥 GVN MASTER ALGO: DHAN API LIVE FEED ENGINE STARTING...")
    print("="*50 + "\n")
    
    with open("dhan_feed_status.log", "w") as f:
        f.write(f"{datetime.now()}: [INIT] Dhan Live Feed Engine Thread Initialized.\n")
        
    thread = threading.Thread(target=live_feed_background_worker, daemon=True)
    thread.start()
    print("[Dhan Live Feed Engine] Started Live API Polling...")
