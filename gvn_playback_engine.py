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
        else:
            price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
            delta = norm_cdf(d1) - 1
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        return price, delta, gamma, 0, 0
    except:
        return 5.0, 0.5, 0.001, 0, 0

# ───────────────────────────────────────────────────────────────
# DYNAMIC PLAYBACK ENGINE
# ───────────────────────────────────────────────────────────────

def _record_trade_db(app, db, AlgoTrade, User, trade):
    with app.app_context():
        try:
            u = User.query.first()
            if u:
                new_trade = AlgoTrade(
                    user_id=u.id, symbol=trade["symbol"], entry_price=trade["entry_price"],
                    quantity=trade["qty"], trade_type='BUY', status='Open',
                    delta=trade["delta"], sentiment=f"Breakout detected at playback"
                )
                db.session.add(new_trade)
                db.session.commit()
                return new_trade.id
        except Exception as e:
            logger.error(f"DB Error: {e}")
    return None

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
    
    orb_candle = candles[0]
    high_915 = float(orb_candle.get('High', orb_candle.get('high', 0)))
    low_915 = float(orb_candle.get('Low', orb_candle.get('low', 0)))
    range_915 = high_915 - low_915
    
    levels = {
        "i1": high_915 + (range_915 * 0.618),
        "i5": high_915 + (range_915 * 1.618),
        "i2": low_915 - (range_915 * 0.618),
        "i6": low_915 - (range_915 * 1.618),
    }
    shared_data.demo_logs.append(f"📅 [ORB] 9:15 AM Candle: High {high_915} | Low {low_915}")
    shared_data.demo_logs.append(f"📈 [INDICATOR] i5 Resistance: {round(levels['i5'],2)} | i2 Support: {round(levels['i2'],2)}")
    
    from app import app, db, AlgoTrade, User
    active_trade = None
    
    for i in range(1, len(candles)):
        if not shared_data.demo_playback_running: break
        candle = candles[i]
        price = float(candle['Close'])
        shared_data.market_data[symbol] = price
        
        # --- GENERATE FULL OPTION CHAIN FOR DASHBOARD ---
        full_chain = []
        spot_strike = int(round(price / 50.0) * 50)
        for s in range(spot_strike - 500, spot_strike + 550, 50):
            c_price, c_delta, c_gamma, c_theta, c_iv = black_scholes(price, s, 0.005, 0.07, 0.12, "CE")
            p_price, p_delta, p_gamma, p_theta, p_iv = black_scholes(price, s, 0.005, 0.07, 0.12, "PE")
            full_chain.append({
                "strike": s,
                "call_ltp": round(c_price, 2), "call_delta": round(c_delta, 2),
                "call_theta": round(c_theta, 2), "call_gamma": round(c_gamma, 4),
                "call_iv": 12.0, "call_volume": 1000, "call_oi": 500,
                "put_ltp": round(p_price, 2), "put_delta": round(p_delta, 2),
                "put_theta": round(p_theta, 2), "put_gamma": round(p_gamma, 4),
                "put_iv": 12.0, "put_volume": 1200, "put_oi": 600
            })
        shared_data.demo_full_chain = full_chain

        if i % 10 == 0:
            shared_data.demo_logs.append(f"🕒 [{candle['Datetime'].strftime('%H:%M')}] {symbol} Spot: {price}")

        if not active_trade:
            if price > levels['i5']:
                strike = spot_strike
                full_sym = f"{symbol}_{strike}_CE"
                c_price, c_delta, c_gamma, c_theta, c_iv = black_scholes(price, strike, 0.005, 0.07, 0.12, "CE")
                entry_price = round(c_price, 2)
                active_trade = {"symbol": full_sym, "entry_price": entry_price, "type": "BUY", "option_type": "CE", "delta": c_delta, "target": entry_price + 20, "sl": entry_price - 15, "qty": 50}
                shared_data.demo_logs.append(f"🚀 [SIGNAL] Bullish Breakout! Buying {full_sym} @ ₹{entry_price}")
                active_trade["db_id"] = _record_trade_db(app, db, AlgoTrade, User, active_trade)
            elif price < levels['i2']:
                strike = spot_strike
                full_sym = f"{symbol}_{strike}_PE"
                p_price, p_delta, p_gamma, p_theta, p_iv = black_scholes(price, strike, 0.005, 0.07, 0.12, "PE")
                entry_price = round(p_price, 2)
                active_trade = {"symbol": full_sym, "entry_price": entry_price, "type": "BUY", "option_type": "PE", "delta": p_delta, "target": entry_price + 20, "sl": entry_price - 15, "qty": 50}
                shared_data.demo_logs.append(f"🔥 [SIGNAL] Bearish Breakdown! Buying {full_sym} @ ₹{entry_price}")
                active_trade["db_id"] = _record_trade_db(app, db, AlgoTrade, User, active_trade)

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
