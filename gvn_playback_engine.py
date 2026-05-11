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
    if T <= 0: return (max(0, S - K) if option_type == "CE" else max(0, K - S)), 1.0, 0, 0, 0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if option_type == "CE":
            price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
            delta = norm_cdf(d1)
            theta = -(S * norm_pdf(d1) * sigma / (2 * math.sqrt(T))) - r * K * math.exp(-r * T) * norm_cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
            delta = norm_cdf(d1) - 1
            theta = -(S * norm_pdf(d1) * sigma / (2 * math.sqrt(T))) + r * K * math.exp(-r * T) * norm_cdf(-d2)
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * norm_pdf(d1) * math.sqrt(T)
        return price, delta, gamma, theta / 365.0, vega / 100.0
    except:
        return 5.0, 0.5, 0.001, -0.01, 0.01

# ───────────────────────────────────────────────────────────────
# DYNAMIC PLAYBACK ENGINE
# ───────────────────────────────────────────────────────────────

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
    """
    GVN Advanced Playback: Real Historical Data Simulation
    """
    shared_data.demo_playback_running = True
    shared_data.demo_logs.append(f"🎬 [DYNAMIC PLAYBACK] Starting {symbol} at {speed}x speed...")
    
    # Load Data
    data = get_real_historical_data(symbol)
    if data is None or len(data) < 10:
        shared_data.demo_logs.append("❌ Could not fetch historical data for playback.")
        shared_data.demo_playback_running = False
        return

    # Extract OHLC
    candles = data.reset_index().to_dict('records')
    
    # 1. 9:15 Candle Capture
    orb_candle = candles[0] # Assuming first candle is 9:15
    high_915 = float(orb_candle['High'])
    low_915 = float(orb_candle['Low'])
    range_915 = high_915 - low_915
    
    shared_data.demo_logs.append(f"📅 [ORB] 9:15 AM Candle: High {high_915} | Low {low_915}")
    
    # Calculate GVN i-Levels (Simplified for Demo)
    levels = {
        "i1": high_915 + (range_915 * 0.618),
        "i5": high_915 + (range_915 * 1.618),
        "i7": high_915 + (range_915 * 2.618),
        "i2": low_915 - (range_915 * 0.618),
        "i6": low_915 - (range_915 * 1.618),
    }
    
    shared_data.demo_logs.append(f"📈 [INDICATOR] Fibonacci i-Levels Calculated. i5 Resistance: {round(levels['i5'],2)}")
    
    from app import app, db, AlgoTrade, User
    import threading

    active_trade = None
    
    # Simulation Loop
    for i in range(1, len(candles)):
        if not shared_data.demo_playback_running: break
        
        candle = candles[i]
        timestamp = candle['Datetime'].strftime('%H:%M')
        price = float(candle['Close'])
        shared_data.market_data[symbol] = price
        
        # Log periodically
        if i % 10 == 0:
            shared_data.demo_logs.append(f"🕒 [{timestamp}] {symbol} Spot: {price}")

        # --- SIGNAL LOGIC ---
        if not active_trade:
            # Bullish Crossover (Price > i1 or i5)
            if price > levels['i5']:
                strike = int(round(price / 50.0) * 50)
                full_sym = f"{symbol}_{strike}_CE"
                
                # Calculate Option Price using Black-Scholes
                opt_price, delta, gamma, theta, iv = black_scholes(price, strike, 0.01, 0.07, 0.15, "CE")
                entry_price = round(opt_price * 10, 2) # Scaled for index
                
                active_trade = {
                    "symbol": full_sym,
                    "entry_price": entry_price,
                    "type": "BUY",
                    "delta": delta,
                    "target": entry_price + 20,
                    "sl": entry_price - 15,
                    "qty": 50
                }
                
                shared_data.demo_logs.append(f"🚀 [SIGNAL] Bullish Breakout above i5! Buying {full_sym} @ ₹{entry_price}")
                
                # Update DB
                with app.app_context():
                    try:
                        u = User.query.first()
                        if u:
                            new_trade = AlgoTrade(
                                user_id=u.id, symbol=full_sym, entry_price=entry_price,
                                quantity=50, trade_type='BUY', status='Open',
                                delta=delta, sentiment="Institutional Breakout at i5"
                            )
                            db.session.add(new_trade)
                            db.session.commit()
                            active_trade["db_id"] = new_trade.id
                    except: pass

        # --- TRADE MANAGEMENT ---
        elif active_trade:
            # Update Current Option Price
            strike = int(active_trade["symbol"].split("_")[1])
            cur_opt, d, g, t, v = black_scholes(price, strike, 0.01, 0.07, 0.15, "CE")
            cur_price = round(cur_opt * 10, 2)
            pnl = (cur_price - active_trade["entry_price"]) * active_trade["qty"]
            
            # Check Exit Conditions
            if cur_price >= active_trade["target"] or cur_price <= active_trade["sl"] or i == len(candles)-1:
                status = "PROFIT" if cur_price >= active_trade["target"] else "LOSS"
                shared_data.demo_logs.append(f"🏁 [EXIT] {active_trade['symbol']} {status} HIT! Exit: ₹{cur_price} | P&L: ₹{round(pnl,2)}")
                
                # Update DB
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
            else:
                # Log running trade every 5 mins
                if i % 5 == 0:
                    shared_data.demo_logs.append(f"⏳ [RUNNING] {active_trade['symbol']} | LTP: {cur_price} | P&L: ₹{round(pnl,2)}")

        # Control playback speed
        time.sleep(1.0 / speed)

    shared_data.demo_playback_running = False
    shared_data.demo_logs.append("🏁 Dynamic Playback Complete.")

if __name__ == "__main__":
    run_playback(speed=10.0)
