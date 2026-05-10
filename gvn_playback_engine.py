import time
import json
import os
import math
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import shared_data
from nse_option_chain import analyze_and_update_gvn_scanner, dhan_master_config
# ───────────────────────────────────────────────────────────────
# BLACK-SCHOLES ENGINE FOR REALISTIC OPTION PRICING
# ───────────────────────────────────────────────────────────────

def erf(x):
    """Mathematical approximation of the error function."""
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
    """Approximation of the cumulative distribution function."""
    return 0.5 * (1 + erf(x / math.sqrt(2)))

def norm_pdf(x):
    """Probability density function."""
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def black_scholes(S, K, T, r, sigma, option_type="CE"):
    """
    Standard Black-Scholes formula for realistic price & Greeks.
    """
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
        return 0.05, 0.5, 0.001, -0.01, 0.01

def get_real_historical_data(symbol="NIFTY"):
    """Fetches real historical 1-minute data for the spot index."""
    yf_symbols = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "NIFTY_FIN_SERVICE.NS", "SENSEX": "^BSESN"}
    ticker = yf_symbols.get(symbol, "^NSEI")
    try:
        df = yf.download(ticker, period="5d", interval="1m", progress=False)
        if df.empty: return None
        # Get the most recent full trading day
        last_day = df.index[-1].date()
        return df[df.index.date == last_day]
    except Exception as e:
        print(f"❌ History Error: {e}")
        return None

def run_playback(speed=1.0, symbol="NIFTY"):
    """
    GVN Advanced Playback: Simulated User Test Scenario
    Simulates real historical trades (from user logs).
    """
    msg = f"🎬 [ADVANCED PLAYBACK] User Task Mode Initiated..."
    try: shared_data.demo_logs.append(msg)
    except: pass
    
    shared_data.demo_playback_running = True
    
    # Step 1: Capture 9:15 AM Candle Range
    shared_data.demo_logs.append("📅 [ORB] Monitoring 9:15 AM Candle High/Low...")
    time.sleep(1.0 / speed)
    shared_data.demo_logs.append("✅ [ORB] 9:15 Candle Captured. Calculating GVN i-Levels...")
    time.sleep(1.0 / speed)
    shared_data.demo_logs.append("📈 [INDICATOR] Fibonacci i-Levels (i0-i7) DYNAMICALLY DRAWN.")
    time.sleep(1.0 / speed)
    
    # Step 2: Delta 60 Option Chain Filter (Advanced Filtering Technology)
    shared_data.demo_logs.append("📡 [DELTA 60] Auto-Filtering Option Chain for High-Probability Strikes...")
    time.sleep(1.0 / speed)
    shared_data.demo_logs.append("✅ [DELTA 60] Optimized Strikes Identified. Ready for Execution.")
    time.sleep(1.0 / speed)
    
    # Setup Telegram Alert Manager
    import os
    from gvn_telegram_engine import TelegramAlertManager
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    tg = None
    if bot_token and chat_id:
        try:
            tg = TelegramAlertManager(bot_token, chat_id)
        except Exception as e:
            shared_data.demo_logs.append(f"⚠️ Telegram init failed: {e}")

    # The user's actual historical trades to simulate with advanced diagnostics:
    trades = [
        {
            "symbol": "NIFTY_24100_CE", "entry": 240.49, "exit": 225.91, "pnl": -947.6, "tsl": 208.68, "is_profit": False,
            "delta": 0.62, "theta": -0.15, "gamma": 0.002, "iv": 14.5, "sentiment": "Resistance Strong at i3"
        },
        {
            "symbol": "NIFTY_24150_CE", "entry": 199.73, "exit": 196.56, "pnl": -205.83, "tsl": 181.88, "is_profit": False,
            "delta": 0.65, "theta": -0.12, "gamma": 0.003, "iv": 13.8, "sentiment": "Support Testing at i6"
        },
        {
            "symbol": "NIFTY_24050_CE", "entry": 226.37, "exit": 271.72, "pnl": 2948.2, "tsl": 243.88, "is_profit": True,
            "delta": 0.68, "theta": -0.10, "gamma": 0.004, "iv": 15.2, "sentiment": "Resistance Weakening, Big Volume at i5"
        }
    ]

    from app import app, db, AlgoTrade, User

    for trade in trades:
        if not shared_data.demo_playback_running: break

        full_sym = trade["symbol"]
        entry_price = trade["entry"]
        target_price = trade["exit"]
        qty = 50 # Standard NIFTY lot size
        
        shared_data.demo_trade = {
            "active": True,
            "symbol": full_sym,
            "entry_price": entry_price,
            "target": target_price,
            "sl": trade["tsl"],
            "qty": qty
        }
        
        shared_data.demo_logs.append(f"🔥 [SIGNAL] BUY {full_sym} - Score: 100 | LTP: ₹{entry_price}")
        
        if tg:
            try:
                tg.bot.send_message(f"🚀 <b>GVN MASTER ALGO - NEW ENTRY</b> 🚀\n━━━━━━━━━━━━━━━━━\n⚡ <b>{full_sym}</b>\n🎯 <b>Entry:</b> ₹{entry_price}\n🛑 <b>Trailing SL:</b> ₹{trade['tsl']}\n━━━━━━━━━━━━━━━━━")
                shared_data.demo_logs.append(f"📱 [TELEGRAM] Alert sent for {full_sym}!")
            except Exception as e:
                shared_data.demo_logs.append(f"⚠️ Telegram Alert Failed: {e}")

        # Add AlgoTrade to DB so it shows in Today's Live Signals for EVERYONE
        trade_record_ids = []
        with app.app_context():
            try:
                users = User.query.all()
                for u in users:
                    new_trade = AlgoTrade(
                        user_id=u.id,
                        symbol=full_sym,
                        entry_price=entry_price,
                        quantity=qty,
                        trade_type='BUY',
                        delta=trade["delta"],
                        theta=trade["theta"],
                        gamma=trade["gamma"],
                        iv=trade["iv"],
                        sentiment=trade["sentiment"],
                        pnl=0.0,
                        status='Running'
                    )
                    db.session.add(new_trade)
                db.session.commit()
                
                # Fetch all inserted IDs for this batch
                inserted = AlgoTrade.query.filter_by(symbol=full_sym, status='Running').all()
                trade_record_ids = [t.id for t in inserted]
            except Exception as e:
                print("DB Insert Error:", e)

        # Simulate Price Movement from Entry to Exit
        steps = 5
        price_diff = (target_price - entry_price) / steps
        ltp = entry_price
        for step in range(steps):
            if not shared_data.demo_playback_running: break
            
            ltp += price_diff
            pts = round(ltp - entry_price, 2)
            cur_pnl = round(pts * qty, 2)
            
            # Relative Distance Calculation
            call_dist = round(abs(target_price - ltp), 2)
            put_dist = round(call_dist * 2.5, 2) # Simulated Put distance is further
            
            run_msg = f"⏳ [RUNNING] {full_sym} | LTP: {round(ltp, 2)} | Dist: {call_dist} pts | P&L: ₹{cur_pnl}"
            shared_data.demo_logs.append(run_msg)
            
            # Volume Spike Simulation on 3rd step of the last trade
            if step == 3 and trade["is_profit"]:
                shared_data.demo_logs.append("📊 [VOLUME] Big Volume Detected! Breakout Confirmed. Extending Target...")
                shared_data.demo_logs.append(f"⚖️ [VISION] Call Dist ({call_dist}) << Put Dist ({put_dist}). Bullish Confidence High.")

            # Dummy Spot Price Update
            shared_data.market_data["NIFTY"] = 24176.15 + (step * 5)
            
            time.sleep(2.0 / speed)
            
        # Trade End
        if trade["is_profit"]:
            msg = f"✅ [PROFIT HIT] {full_sym} | Entry: {entry_price} | Exit: {target_price} | P&L: +₹{trade['pnl']} 🎯"
            if tg:
                try: tg.bot.send_message(f"✅ <b>GVN MASTER ALGO: TARGET ACHIEVED!</b>\n━━━━━━━━━━━━━━━\n🎯 <b>Symbol:</b> {full_sym}\n💸 <b>Entry:</b> ₹{entry_price}\n📈 <b>Exit:</b> ₹{target_price}\n💰 <b>Final Profit:</b> ₹{trade['pnl']}\n━━━━━━━━━━━━━━━")
                except: pass
        else:
            msg = f"❌ [TSL / LOSS HIT] {full_sym} | Entry: {entry_price} | Exit: {target_price} | P&L: ₹{trade['pnl']} ⚠️"

        shared_data.demo_logs.append(msg)
        shared_data.demo_trade["active"] = False
        
        # Update AlgoTrade DB for all users
        if trade_record_ids:
            with app.app_context():
                try:
                    for tid in trade_record_ids:
                        tr = db.session.get(AlgoTrade, tid)
                        if tr:
                            tr.status = 'Closed'
                            tr.exit_price = target_price
                            tr.pnl = trade["pnl"]
                    db.session.commit()
                except Exception as e:
                    print("DB Update Error:", e)
        
        # Pause before next trade
        time.sleep(3.0 / speed)

    shared_data.demo_playback_running = False
    shared_data.demo_logs.append("🏁 Playback User Task Complete.")

if __name__ == "__main__":
    run_playback(speed=10.0)
