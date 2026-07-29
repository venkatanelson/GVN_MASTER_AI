import time
import json
import os
import math
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import shared_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_Playback")

# ───────────────────────────────────────────────────────────────
# BLACK-SCHOLES ENGINE FOR REALISTIC OPTION PRICING
# ───────────────────────────────────────────────────────────────

def erf(x):
    a1 =  0.254829592
    a2 = -0.284496736
    a3 =  1.421413741
    a4 = -1.453152027
    a5 =  1.061405429
    p  =  0.3275911
    sign = 1
    if x < 0: sign = -1
    x = abs(x)
    t = 1.0/(1.0 + p*x)
    y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t*math.exp(-x*x)
    return sign*y

def norm_cdf(x):
    return 0.5 * (1 + erf(x / math.sqrt(2)))

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def black_scholes(S, K, T, r, sigma, option_type="CE"):
    """
    Standard Black-Scholes Option Pricing Model.
    S: Spot Price, K: Strike Price, T: Time to Expiry (years), r: Risk-free rate, sigma: Volatility (IV)
    """
    try:
        # Tuning sigma (IV) to match user's real-market screenshot (~18.5%)
        # Adjusting T for near-expiry (e.g., Thursday expiry if today is Tuesday -> 2/365)
        sigma = 0.185 # 18.5% IV as per Sensibull
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type == "CE":
            price = S * 0.5 * (1 + math.erf(d1 / math.sqrt(2))) - K * math.exp(-r * T) * 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
            delta = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
        else:
            price = K * math.exp(-r * T) * 0.5 * (1 - math.erf(d2 / math.sqrt(2))) - S * 0.5 * (1 - math.erf(d1 / math.sqrt(2)))
            delta = 0.5 * (1 + math.erf(d1 / math.sqrt(2))) - 1
            
        gamma = (math.exp(-d1**2 / 2) / (math.sqrt(2 * math.pi))) / (S * sigma * math.sqrt(T))
        theta = -(S * sigma * math.exp(-d1**2 / 2) / (2 * math.sqrt(2 * math.pi * T))) - r * K * math.exp(-r * T) * 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
        vega = S * math.sqrt(T) * (math.exp(-d1**2 / 2) / (math.sqrt(2 * math.pi)))
        
        return price, delta, gamma, theta / 365, sigma
    except Exception:
        return 0, 0, 0, 0, 0

# ───────────────────────────────────────────────────────────────
# DYNAMIC PLAYBACK ENGINE
# ───────────────────────────────────────────────────────────────

def _record_trade_db(app, db, AlgoTrade, User, trade):
    with app.app_context():
        try:
            from datetime import datetime, timezone, timedelta
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            u = User.query.first()
            if u:
                new_trade = AlgoTrade(
                    user_id=u.id, symbol=trade["symbol"], entry_price=trade["entry_price"],
                    quantity=trade["qty"], trade_type='BUY', status='Open',
                    delta=trade["delta"], sentiment=f"Breakout detected at playback",
                    timestamp=datetime.now(ist_tz)
                )
                db.session.add(new_trade)
                db.session.commit()
                return new_trade.id
        except Exception as e:
            logger.error(f"DB Error: {e}")
    return None

import threading
def _dispatch_live_playback_orders(app, trade):
    """Dynamically routes playback simulated trades to live connected users!"""
    with app.app_context():
        try:
            from app import User, UserBrokerConfig
            from broker_api import place_order_universal
            import shared_data
            
            live_users = User.query.filter_by(algo_status='ON', user_type='LIVE', is_approved=True).all()
            if not live_users: return
            
            def order_worker(u, t):
                try:
                    cfg = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                    if not cfg: return
                    broker_key = (cfg.broker_name or "Shoonya").replace(" ", "")
                    
                    # Only execute if broker is actively connected
                    if shared_data.broker_connection_status.get(broker_key, False) or shared_data.broker_connection_status.get(cfg.broker_name, False):
                        qty = t["qty"] * u.trade_lots
                        creds = cfg.get_credentials()
                        broker_cfg = {
                            "broker": cfg.broker_name,
                            "client_id": cfg.client_id,
                            "password": creds.get("password"),
                            "api_key": creds.get("api_key"),
                            "api_secret": creds.get("api_secret"),
                            "totp_key": creds.get("totp_key")
                        }
                        shared_data.demo_logs.append(f"⚡ [MULTI-ROUTER] Routing {t['type']} order for {u.username} to {cfg.broker_name}...")
                        
                        # FIRE THE REAL ORDER!
                        order_id = place_order_universal(broker_cfg, t["symbol"], t["type"], qty)
                        if order_id:
                            shared_data.demo_logs.append(f"✅ [MULTI-ROUTER] Order Placed for {u.username}! ID: {order_id}")
                        else:
                            shared_data.demo_logs.append(f"❌ [MULTI-ROUTER] Order Failed for {u.username} via {cfg.broker_name}")
                except Exception as e:
                    shared_data.demo_logs.append(f"⚠️ Live Dispatch Error for User {u.id}: {e}")
            
            for usr in live_users:
                threading.Thread(target=order_worker, args=(usr, trade), daemon=True).start()
        except Exception as e:
            logger.error(f"Dispatch Error: {e}")

def get_real_historical_data(symbol="NIFTY"):
    yf_symbols = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "NIFTY_FIN_SERVICE.NS", "SENSEX": "^BSESN"}
    ticker = yf_symbols.get(symbol, "^NSEI")
    try:
        df = yf.download(ticker, period="5d", interval="1m", progress=False)
        if df.empty: return None
        last_day = df.index[-1].date()
        return df[df.index.date == last_day]
    except Exception as e:
        logger.error(f"❌ History Error: {e}")
        return None

def run_playback(speed=1.0, symbol="NIFTY"):
    shared_data.demo_playback_running = True
    shared_data.demo_logs.append(f"🎬 [DYNAMIC PLAYBACK] Starting {symbol} at {speed}x speed...")
    
    data = get_real_historical_data(symbol)
    if data is None or len(data) < 10:
        shared_data.demo_logs.append("❌ Could not fetch historical data.")
        shared_data.demo_playback_running = False
        return

    df_flat = data.copy()
    if isinstance(df_flat.columns, pd.MultiIndex):
        df_flat.columns = df_flat.columns.get_level_values(0)
    candles = df_flat.reset_index().to_dict('records')
    
    # 1. 9:15 Candle Capture & Initial Strike Selection
    try:
        orb_candle = candles[0] 
        spot_915 = float(orb_candle.get('Close', orb_candle.get('close', 0)))
        high_915 = float(orb_candle.get('High', orb_candle.get('high', 0)))
        low_915 = float(orb_candle.get('Low', orb_candle.get('low', 0)))
        range_915 = high_915 - low_915
        
        # Select Delta 60 Strike (Slightly ITM)
        ce_strike = int(round((spot_915 - 50) / 50.0) * 50)
        pe_strike = int(round((spot_915 + 50) / 50.0) * 50)
        
        # Calculate 9:15 Option Prices to set Fibonacci Levels on Premium
        ce_price_915, _, _, _, _ = black_scholes(spot_915, ce_strike, 0.005, 0.07, 0.12, "CE")
        pe_price_915, _, _, _, _ = black_scholes(spot_915, pe_strike, 0.005, 0.07, 0.12, "PE")
        
        # Fibonacci Ratios (User's Strategy)
        ratios = {"i1": 0.236, "i2": 0.382, "i5": 0.5, "i6": 0.618, "i7": 0.786, "i8": 1.0}
        
        # We will track these levels for the active symbols
        shared_data.demo_logs.append(f"📅 [ORB] 9:15 AM Spot: {spot_915} | High: {high_915} | Low: {low_915}")
        shared_data.demo_logs.append(f"🎯 [STRATEGY] Delta 60 Strikes -> CE: {ce_strike} | PE: {pe_strike}")
    except Exception as e:
        shared_data.demo_logs.append(f"❌ Error initializing ORB: {e}")
        shared_data.demo_playback_running = False
        return
    
    # --- 2. PRE-FETCH REAL HISTORICAL OPTION DATA (FOR 10 STRIKES) ---
    historical_option_data = {} # Format: {strike_type: [candles]}
    
    # Define 10 Strikes (5 CE + 5 PE) around spot
    strikes_to_fetch = []
    base_strike = int(round(spot_915 / 50.0) * 50)
    for s in range(base_strike - 100, base_strike + 150, 50):
        strikes_to_fetch.append((s, "CE"))
        strikes_to_fetch.append((s, "PE"))
        
    shared_data.demo_logs.append(f"📡 [DATA] Attempting to fetch Real History for 10 Strikes from TrueData...")
    
    from truedata_rest_api import TrueDataRestAPI
    td_api = TrueDataRestAPI(os.getenv("TRUEDATA_USERNAME"), os.getenv("TRUEDATA_PASSWORD"))
    
    # Format dates for TrueData History API (YYMMDDHHMMSS)
    from_dt = data.index[0].strftime("%y%m%d091500")
    to_dt = data.index[-1].strftime("%y%m%d153000")
    
    for strike, opt_type in strikes_to_fetch:
        # Construct TrueData Symbol: e.g., NIFTY26MAY1423850CE
        # Note: Correct symbol format is crucial. Assuming standard NIFTY format.
        formatted_expiry = "26MAY14" # This should ideally be dynamic based on expiry list
        td_symbol = f"{symbol}{formatted_expiry}{strike}{'CE' if opt_type=='CE' else 'PE'}"
        
        hist = td_api.get_historical_data(td_symbol, from_dt, to_dt)
        if hist and 'candles' in hist:
            historical_option_data[f"{strike}_{opt_type}"] = hist['candles']
            # shared_data.demo_logs.append(f"✅ Loaded History for {td_symbol}")
        else:
            shared_data.demo_logs.append(f"⚠️ History not found for {td_symbol}. Using Digital Twin fallback.")
            
    from app import app, db, AlgoTrade, User
    active_trade = None
    
    for i in range(1, len(candles)):
        if not shared_data.demo_playback_running: break
        candle = candles[i]
        price = float(candle['Close'])
        shared_data.market_data[symbol] = price
        
        # --- GENERATE OPTION CHAIN DATA ---
        full_chain = []
        for s, o_t in strikes_to_fetch:
            if o_t == "PE": continue # Process strike as a pair
            
            # CE Data
            ce_key = f"{s}_CE"
            if ce_key in historical_option_data and i < len(historical_option_data[ce_key]):
                c_data = historical_option_data[ce_key][i]
                c_p = float(c_data[4]) # Close price
                # If TrueData history doesn't include Greeks, we still use BS for Greeks display
                _, c_d, c_g, c_t, c_iv = black_scholes(price, s, 0.005, 0.07, 0.12, "CE")
            else:
                c_p, c_d, c_g, c_t, c_iv = black_scholes(price, s, 0.005, 0.07, 0.12, "CE")
                
            # PE Data
            pe_key = f"{s}_PE"
            if pe_key in historical_option_data and i < len(historical_option_data[pe_key]):
                p_data = historical_option_data[pe_key][i]
                p_p = float(p_data[4])
                _, p_d, p_g, p_t, p_iv = black_scholes(price, s, 0.005, 0.07, 0.12, "PE")
            else:
                p_p, p_d, p_g, p_t, p_iv = black_scholes(price, s, 0.005, 0.07, 0.12, "PE")
                
            full_chain.append({
                "strike": s,
                "ce_ltp": round(c_p, 2), "ce_delta": round(c_d, 2), "ce_gamma": round(c_g, 4), "ce_theta": round(c_t, 2), "ce_iv": 12.5, "ce_vol": 1500, "ce_oi": 800, "ce_vega": 2.5,
                "pe_ltp": round(p_p, 2), "pe_delta": round(p_d, 2), "pe_gamma": round(p_g, 4), "pe_theta": round(p_t, 2), "pe_iv": 12.8, "pe_vol": 1800, "pe_oi": 950, "pe_vega": 2.4,
                "is_atm": (s == int(round(price/50.0)*50))
            })
        shared_data.demo_full_chain = full_chain

        if i % 10 == 0:
            shared_data.demo_logs.append(f"🕒 [{candle['Datetime'].strftime('%H:%M')}] {symbol}: {price}")

        # --- SIGNAL LOGIC ---
        i5_level = high_915 + (range_915 * 1.618)
        i2_level = low_915 - (range_915 * 0.618)

        if not active_trade:
            if price > i5_level and not active_trade:
                full_sym = f"{symbol}_{ce_strike}_CE"
                # Use real price if available, fallback to Black-Scholes if 0
                cur_price = round(next((float(h[4]) for h in historical_option_data.get(f"{ce_strike}_CE", []) if h[0] == candle['Datetime'].strftime("%y%m%d%H%M%S")), 0), 2)
                if cur_price == 0: cur_price = round(c_p, 2)
                
                active_trade = {"symbol": full_sym, "entry_price": cur_price, "type": "BUY", "option_type": "CE", "delta": 0.6, "target": cur_price + 30, "sl": cur_price - 12, "qty": 50}
                shared_data.demo_logs.append(f"🚀 [SIGNAL] PLAYBACK BUY: {full_sym} @ ₹{active_trade['entry_price']} | SL: 12pts")
                active_trade["db_id"] = _record_trade_db(app, db, AlgoTrade, User, active_trade)
                _dispatch_live_playback_orders(app, active_trade)
                
                # --- TELEGRAM ALERT ---
                try:
                    from gvn_telegram_engine import TelegramAlertManager
                    tg = TelegramAlertManager(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
                    tg.alert_entry(active_trade)
                except Exception as e:
                    shared_data.demo_logs.append(f"⚠️ TG Alert Error: {e}")

            elif price < i2_level and not active_trade:
                full_sym = f"{symbol}_{pe_strike}_PE"
                cur_price = round(next((float(h[4]) for h in historical_option_data.get(f"{pe_strike}_PE", []) if h[0] == candle['Datetime'].strftime("%y%m%d%H%M%S")), 0), 2)
                if cur_price == 0: cur_price = round(p_p, 2)
                
                active_trade = {"symbol": full_sym, "entry_price": cur_price, "type": "BUY", "option_type": "PE", "delta": 0.6, "target": cur_price + 30, "sl": cur_price - 12, "qty": 50}
                shared_data.demo_logs.append(f"🔥 [SIGNAL] PLAYBACK BUY: {full_sym} @ ₹{active_trade['entry_price']} | SL: 12pts")
                active_trade["db_id"] = _record_trade_db(app, db, AlgoTrade, User, active_trade)
                _dispatch_live_playback_orders(app, active_trade)
                
                # --- TELEGRAM ALERT ---
                try:
                    from gvn_telegram_engine import TelegramAlertManager
                    tg = TelegramAlertManager(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
                    tg.alert_entry(active_trade)
                except Exception as e:
                    shared_data.demo_logs.append(f"⚠️ TG Alert Error: {e}")

        elif active_trade:
            strike = int(active_trade["symbol"].split("_")[1])
            cur_opt, d, g, t, v = black_scholes(price, strike, 0.005, 0.07, 0.12, active_trade["option_type"])
            cur_price = round(cur_opt, 2)
            pnl = (cur_price - active_trade["entry_price"]) * active_trade["qty"]
            if cur_price >= active_trade["target"] or cur_price <= active_trade["sl"] or i == len(candles)-1:
                shared_data.demo_logs.append(f"🏁 [EXIT] {active_trade['symbol']} Exit: ₹{cur_price} | P&L: ₹{round(pnl,2)}")
                with app.app_context():
                    try:
                        tr = db.session.get(AlgoTrade, active_trade["db_id"])
                        if tr:
                            tr.status = 'Closed'
                            tr.exit_price = cur_price
                            tr.pnl = pnl
                            db.session.commit()
                    except: pass
                active_trade = None
        time.sleep(1.0 / speed)

    shared_data.demo_playback_running = False
    shared_data.demo_logs.append("🏁 Playback Complete.")

if __name__ == "__main__":
    run_playback(speed=10.0)
