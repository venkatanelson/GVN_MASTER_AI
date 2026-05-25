
import time
import json
import logging
from datetime import datetime
import nse_option_chain
import gvn_levels_engine
from gvn_telegram_engine import TelegramAlertManager
from gvn_paper_trading_engine import PaperTradingManager
from broker_api import place_order_universal
import shared_data
import gvn_data_bank

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_AI_Delta60")

class GVNAiDelta60Engine:
    """
    GVN Master AI Brain v8.0 - Maximum Safety Edition
    - Integrated Admin Kill Switch
    - Auto Square-off on Kill/OFF status
    - Dynamic Position Sizing (Capital Based)
    - Multi-Stage Exit Strategy
    """
    
    def __init__(self, bot_token=None, chat_id=None):
        self.memory = {
            "active_trades": {},
            "oi_trend": "NEUTRAL"
        }
        self.indices = ["NIFTY", "BANKNIFTY"]
        self.is_running = False
        
        if bot_token and chat_id:
            self.telegram = TelegramAlertManager(bot_token, chat_id)
        else:
            self.telegram = None
            
        self.paper_trading = PaperTradingManager().get_executor()
        self.last_cleanup_date = None
        self.last_snapshot_time = 0
        gvn_data_bank.init_db()

    def run_ai_loop(self):
        self.is_running = True
        logger.info("🛡️ [GVN SAFETY BRAIN v8.0] Kill-Switch & Auto-Square-off Active...")
        
        while self.is_running:
            try:
                # 🛡️ SAFETY CHECK: Is Algo ON or Kill Switch Active?
                if not self._check_safety_status():
                    time.sleep(5)
                    continue

                # 🧹 WEEKLY EXPIRY CLEANUP
                self._handle_weekly_cleanup()

                for index in self.indices:
                    chain = nse_option_chain.fetch_nse_option_chain(index)
                    if not chain or "records" not in chain: continue
                    
                    records = chain["records"]
                    spot = records.get("underlyingValue", shared_data.market_data.get(index, 25000))
                    
                    # 1. Update Market Score
                    self._sync_sentiment(records)
                    
                    # 📊 AI STATUS LOG (Every 30 seconds)
                    if int(time.time()) % 30 < 2:
                        score = shared_data.market_pulse.get("score", 0)
                        logger.info(f"🤖 [AI BRAIN] {index} Spot: {spot} | Market Score: {score} | Trades: {len(self.memory['active_trades'])}")

                    # 2. Monitor & Execute
                    strikes = self._pick_alpha_strikes(records, spot, index)
                    
                    # 📸 PERIODIC SNAPSHOT (Every 5 minutes)
                    if time.time() - self.last_snapshot_time > 300:
                        self._save_market_snapshot(index, strikes)
                        self.last_snapshot_time = time.time()

                    for strike in strikes:
                        self._manage_trade_cycle(index, strike)
                
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Safety Loop Error: {e}")
                time.sleep(5)

    def _check_safety_status(self):
        """Checks DB for Kill Switch or OFF status and squares off if needed"""
        # This reads from the shared_data which is updated by app.py
        is_killed = shared_data.market_pulse.get("admin_kill_switch", False)
        is_off = shared_data.market_pulse.get("algo_status", "OFF") == "OFF"
        
        if is_killed or is_off:
            if self.memory["active_trades"]:
                logger.warning("🚨 [KILL SWITCH] Squaring off all positions immediately!")
                if self.telegram: self.telegram.send_alert("🚨 <b>ADMIN KILL SWITCH ACTIVATED</b> 🚨\nSquaring off all positions!")
                
                # Close all active trades
                for key in list(self.memory["active_trades"].keys()):
                    trade = self.memory["active_trades"][key]
                    # Simulate or Execute SELL Order for all lots
                    self._fire_order(key.split('_')[0], {"ltp": 0, "strike": key.split('_')[0], "type": key.split('_')[1]}, "SELL", trade["total_lots"], "EMERGENCY SQUARE-OFF")
                
                self.memory["active_trades"] = {}
            return False
        return True

    def _handle_weekly_cleanup(self):
        """Runs cleanup at 6:00 PM (18:00) every Thursday (Expiry Day)"""
        now = datetime.now()
        # Thursday is weekday 3 (Monday is 0)
        if now.weekday() == 3 and now.hour == 18 and now.minute == 0 and self.last_cleanup_date != now.date():
            logger.info("🧹 [GVN WEEKLY CLEANUP] Starting Expiry Day database maintenance...")
            gvn_data_bank.cleanup_old_data(days=7)
            self.last_cleanup_date = now.date()
            if self.telegram:
                self.telegram.send_alert("🧹 <b>GVN WEEKLY CLEANUP</b>\nExpiry Day maintenance complete. Data Bank refreshed for next cycle.")

    def _save_market_snapshot(self, symbol, strikes):
        """Saves current strikes data to the Data Bank"""
        gvn_data_bank.save_option_snapshot(symbol, strikes)
        logger.info(f"📸 [GVN DATA BANK] Saved snapshot for {symbol}")

    def _sync_sentiment(self, records):
        tot_ce = records.get("filtered", {}).get("CE", {}).get("totOI", 1)
        tot_pe = records.get("filtered", {}).get("PE", {}).get("totOI", 1)
        ratio = tot_pe / tot_ce
        shared_data.market_pulse["score"] = int(min(ratio * 50, 100))

    def _pick_alpha_strikes(self, records, spot, symbol):
        is_expiry = datetime.now().weekday() in [2, 3]
        target_d = 0.50 if is_expiry else 0.62
        alpha_grid = []
        for item in records.get("data", []):
            for t in ["CE", "PE"]:
                if t in item:
                    opt = item[t]
                    delta = abs(opt.get("delta", 0.5))
                    if 0.40 <= delta <= 0.75:
                        alpha_grid.append({
                            "strike": item["strikePrice"], "type": t,
                            "ltp": opt.get("lastPrice", 0), "delta": delta,
                            "high_915": opt.get("high_915", opt.get("lastPrice", 0) + 15),
                            "low_915": opt.get("low_915", opt.get("lastPrice", 0) - 15),
                            "symbol": opt.get("symbol") or opt.get("tradingSymbol") or f"{symbol}{item['strikePrice']}{t}"
                        })
        return sorted(alpha_grid, key=lambda x: abs(x["delta"] - target_d))[:14]

    def _manage_trade_cycle(self, symbol, strike):
        key = f"{strike['strike']}_{strike['type']}"
        ltp = strike["ltp"]
        # ⚡ REAL-TIME WEBSOCKET LTP OVERRIDE (Sub-second execution)
        search_key = f"{int(strike['strike'])} {strike['type']}"
        real_ltp = shared_data.market_data.get(search_key, 0)
        if real_ltp > 0:
            ltp = real_ltp
        levels = gvn_levels_engine.calculate_gvn_levels(strike["high_915"], strike["low_915"])
        if not levels: return
        
        # 🔒 PERSISTENT MORNING LOCK: Only allow trades on the morning locked strike
        locked_strike = 0
        try:
            import os
            import json
            if os.path.exists("morning_locked_strikes.json"):
                with open("morning_locked_strikes.json", "r") as f:
                    lock_data = json.load(f)
                if lock_data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                    locked_strike = lock_data.get(symbol, {}).get(strike["type"], 0)
        except: pass

        if locked_strike > 0 and int(strike["strike"]) != locked_strike:
            # Skip new entries for non-locked strikes, but manage active trades if they exist
            if key not in self.memory["active_trades"]:
                return
        
        if "alerted_levels" not in self.memory:
            self.memory["alerted_levels"] = {}

        if key not in self.memory["active_trades"]:
            # CE Entry: Bullish Sentiment (Score >= 65) or UP WIND
            # PE Entry: Bearish Sentiment (Score <= 35) or DOWN WIND
            wind_dir = shared_data.market_pulse.get("wind_direction", "NEUTRAL")
            wind_power = shared_data.market_pulse.get("wind_power", 1.0)
            
            is_bullish = strike['type'] == 'CE' and (shared_data.market_pulse.get("score", 50) >= 65 or any(w in wind_dir for w in ["UP WIND", "SHORT COVERING"]))
            is_bearish = strike['type'] == 'PE' and (shared_data.market_pulse.get("score", 50) <= 35 or any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING"]))
            
            # 🛡️ THE GVN WIND FILTER (AVOIDING 12-PT SL HITS)
            # 1. Reject CE entries if the wind is blowing DOWN
            if strike['type'] == 'CE' and any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING"]):
                is_bullish = False
            # 2. Reject PE entries if the wind is blowing UP
            if strike['type'] == 'PE' and any(w in wind_dir for w in ["UP WIND", "SHORT COVERING"]):
                is_bearish = False
            # 3. Reject ALL entries if it's a Trap / Premium Eating zone
            if "PREMIUM EATING" in wind_dir or wind_power < 0.8:
                is_bullish = False
                is_bearish = False

            # 4. 🛡️ F&O NIFTY 50 UNDERLYING STOCKS ALIGNMENT FILTER (Second Additional Confirmation)
            nifty50_trend = shared_data.market_pulse.get("nifty50_trend_signal", "NEUTRAL")
            if nifty50_trend in ["STRONG BEARISH", "MODERATE BEARISH"] and strike['type'] == 'CE':
                logger.info(f"🚫 [NIFTY 50 STOCK FILTER] CE entry blocked. Nifty 50 trend is {nifty50_trend}.")
                is_bullish = False
            if nifty50_trend in ["STRONG BULLISH", "MODERATE BULLISH"] and strike['type'] == 'PE':
                logger.info(f"🚫 [NIFTY 50 STOCK FILTER] PE entry blocked. Nifty 50 trend is {nifty50_trend}.")
                is_bearish = False

            # Store previous price to detect crossover/touch
            if "last_ltps" not in self.memory:
                self.memory["last_ltps"] = {}
            previous_ltp = self.memory["last_ltps"].get(key, ltp)
            self.memory["last_ltps"][key] = ltp
            
            # GVN Pro Alerts - Check proximity (1% or 1 point buffer) to i5, i6, i7
            if "pro_alerts_sent" not in self.memory:
                self.memory["pro_alerts_sent"] = {}
                
            for lvl_name in ["i5", "i6", "i7"]:
                lvl_val = levels.get(lvl_name, 0)
                if lvl_val > 0:
                    dist = abs(ltp - lvl_val)
                    # Check if within 1 point or 1% buffer
                    if dist <= 1.0 or dist <= (lvl_val * 0.01):
                        alert_time_key = f"{key}_{lvl_name}_pro_alert"
                        last_alert_time = self.memory["pro_alerts_sent"].get(alert_time_key, 0)
                        # Alert at most once every 5 minutes per level per strike
                        if time.time() - last_alert_time > 300:
                            alert_msg = (
                                f"⚠️ <b>GVN PRO ALERT: APPROACHING {lvl_name.upper()}</b> ⚠️\n"
                                f"🎯 Symbol: {symbol} {strike['strike']} {strike['type']}\n"
                                f"⚡ Level: <b>{lvl_name.upper()} ({lvl_val})</b>\n"
                                f"💸 Current Price: <b>₹{ltp}</b>\n"
                                f"📏 Distance: {round(dist, 2)} pts away"
                            )
                            logger.info(f"[PRO ALERT] {symbol} {strike['strike']} {strike['type']} is approaching {lvl_name.upper()} ({lvl_val}) @ {ltp}")
                            if self.telegram:
                                self.telegram.send_alert(alert_msg)
                            self.memory["pro_alerts_sent"][alert_time_key] = time.time()

            # GVN Levels sorted in ascending order: [i1, i7, i6, i5, i3, i2, i0]
            sorted_lvls = sorted([levels['i1'], levels['i7'], levels['i6'], levels['i5'], levels['i3'], levels['i2'], levels['i0']])
            
            # Find the levels crossover and execute trade
            for idx, lvl in enumerate(sorted_lvls):
                # Ensure there is a target level above the entry level
                if idx + 1 >= len(sorted_lvls):
                    continue
                target_lvl = sorted_lvls[idx + 1]
                
                # Crossover/touch condition
                is_triggered = False
                if previous_ltp < lvl <= ltp:
                    is_triggered = True
                elif abs(ltp - lvl) <= 0.20:
                    is_triggered = True
                    
                if is_triggered:
                    is_allowed = True
                    is_exp = (datetime.now().weekday() == 3)
                    
                    # Morning preference check
                    pref_level_val = levels["i1"] if is_exp else levels["i5"]
                    pref_key = f"{key}_pref_traded"
                    
                    # Force first morning entry to be near preference level
                    if not self.memory.get(pref_key, False):
                        if abs(lvl - pref_level_val) > 1.5:
                            is_allowed = False
                            
                    if is_allowed and ((strike['type'] == 'CE' and is_bullish) or (strike['type'] == 'PE' and is_bearish)):
                        sl = lvl - 12.0
                        self.memory[pref_key] = True
                        
                        # Find matching level name from the engine's levels dictionary
                        lvl_name = "Unknown"
                        for k, v in levels.items():
                            if abs(v - lvl) < 0.01:
                                lvl_name = k.upper()
                                break
                        
                        # Execute
                        self._execute_gvn_level_trade(symbol, strike, lvl, target_lvl, sl, f"GVN Level Entry ({lvl_name} @ {lvl:.2f})")
                        break
        else:
            trade = self.memory["active_trades"][key]
            
            # Exit check: Target Hit
            if ltp >= trade["target"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"], f"Full Exit (Target Hit @ {trade['target']})")
                paper_id = trade.get("paper_id")
                if paper_id:
                    self.paper_trading.execute_paper_sell(paper_id, exit_price=ltp, exit_reason="TARGET_HIT")
                del self.memory["active_trades"][key]
                
            # Exit check: Stop Loss Hit
            elif ltp <= trade["sl"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"], f"Full Exit (SL Hit @ {trade['sl']})")
                paper_id = trade.get("paper_id")
                if paper_id:
                    self.paper_trading.execute_paper_sell(paper_id, exit_price=ltp, exit_reason="SL_HIT")
                del self.memory["active_trades"][key]

    def _execute_gvn_level_trade(self, symbol, strike, entry_price, target, sl, reason):
        balance = shared_data.market_data.get("available_cash", 20000)
        target_lots = max(1, min(5, int(balance / 10000)))
        key = f"{strike['strike']}_{strike['type']}"
        
        # Execute paper trade and store the ID
        paper_trade = self.paper_trading.execute_paper_buy(symbol, strike["strike"], strike["type"], entry_price, target, sl, target_lots * 50)
        paper_id = paper_trade["id"] if paper_trade else None
        
        self.memory["active_trades"][key] = {
            "entry": entry_price, 
            "target": target, 
            "sl": sl, 
            "total_lots": target_lots,
            "paper_id": paper_id
        }
        self._fire_order(symbol, strike, "BUY", target_lots, reason, target_price=target, sl_price=sl)

    def _fire_order(self, symbol, strike, side, qty, reason, target_price=None, sl_price=None):
        full_symbol = strike.get("symbol", f"{symbol}{strike['strike']}{strike['type']}")
        tsym = f"{symbol}_{int(strike['strike'])}_{strike['type']}"
        
        if side == "SELL":
            alert = (
                f"🛑 <b>GVN MASTER ALGO - POSITION CLOSED</b> 🛑\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Symbol: <b>{tsym}</b>\n"
                f"⚡ Reason: <b>{reason}</b>\n"
                f"💸 Exit Price: <b>₹{strike.get('ltp', 0.0)}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Position closed successfully"
            )
            if self.telegram: self.telegram.send_alert(alert)
        else:
            # Calculate levels to display in the alert
            levels = gvn_levels_engine.calculate_gvn_levels(strike["high_915"], strike["low_915"])
            if target_price is None:
                target_price = strike.get("ltp", 0.0) + 12.0
            if sl_price is None:
                sl_price = strike.get("ltp", 0.0) - 12.0
            
            level_name = "I3"
            if "i5" in reason.lower(): level_name = "I5"
            elif "i7" in reason.lower(): level_name = "I7"
            elif "i1" in reason.lower() or "i0" in reason.lower(): level_name = "I1/I0"
            elif "i6" in reason.lower(): level_name = "I6"
            elif "i2" in reason.lower(): level_name = "I2"
            elif "i3" in reason.lower(): level_name = "I3"
            
            if levels and target_price is None:
                if level_name == "I5":
                    target_price, sl_price = levels["i3"], round(levels["i6"] - 12.0, 2)
                elif level_name == "I7":
                    target_price, sl_price = levels["i5"], round(levels["i7"] - 12.0, 2)
                elif level_name == "I1/I0":
                    target_price, sl_price = levels["i5"], round(levels["i1"] - 12.0, 2)
                elif level_name == "I6":
                    target_price, sl_price = levels["i3"], round(levels["i6"] - 12.0, 2)
                elif level_name == "I3":
                    target_price, sl_price = levels["i2"], round(levels["i3"] - 12.0, 2)

            alert = (
                f"🚀 <b>GVN MASTER ALGO - NEW ENTRY</b> 🚀\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Symbol: <b>{tsym}</b>\n"
                f"⚡ Level Triggered: <b>{level_name}</b>\n"
                f"💸 Entry Price: <b>₹{strike.get('ltp', 0.0)}</b>\n"
                f"✅ Target: <b>₹{target_price:.2f}</b>\n"
                f"⛔ Stop Loss: <b>₹{sl_price:.2f}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Processed exactly as per GVN Settings"
            )
            if self.telegram: self.telegram.send_alert(alert)

        # 🚀 GVN MULTI-USER DYNAMIC ROUTING ENGINE
        try:
            from app import app, db, User, UserBrokerConfig, AlgoTrade
            
            with app.app_context():
                # Query all active users whose Algo is turned ON and are not blocked
                active_users = User.query.filter_by(algo_status='ON', is_blocked=False).all()
                logger.info(f"🛰️ [GVN MULTI-USER ENGINE] Found {len(active_users)} active users with Algo ON.")
                
                for u in active_users:
                    try:
                        user_lots = u.trade_lots or 1
                        
                        # 1. Check if user has active and approved live subscription
                        is_live_allowed = False
                        if u.user_type == 'LIVE' and u.is_approved:
                            if u.expiry_date and u.expiry_date > datetime.utcnow():
                                is_live_allowed = True
                        
                        # 2. Add trade to their database dashboard
                        new_trade = AlgoTrade(
                            user_id=u.id,
                            symbol=full_symbol,
                            entry_price=float(strike['ltp']) if side == 'BUY' else 0.0,
                            exit_price=float(strike['ltp']) if side == 'SELL' else 0.0,
                            quantity=user_lots * 50, # 1 lot = 50 qty
                            trade_type=side,
                            status='Open' if side == 'BUY' else 'Closed',
                            delta=float(strike.get('delta', 0.60)),
                            sentiment=reason
                        )
                        db.session.add(new_trade)
                        db.session.commit()
                        
                        # 3. If LIVE subscription and API is configured, place REAL trade
                        config = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                        if is_live_allowed and config and config.client_id:
                            creds = config.get_credentials()
                            cfg = {
                                "broker_name": config.broker_name or "Shoonya",
                                "client_id": config.client_id,
                                "password": creds.get('password'),
                                "api_key": creds.get('api_key'),
                                "api_secret": creds.get('api_secret'),
                                "totp_key": creds.get('totp_key'),
                                "webhook_url": config.webhook_url,
                                "tv_secret": config.tv_secret
                            }
                            
                            from broker_api import execute_broker_order_async
                            execute_broker_order_async(cfg, full_symbol, side, user_lots * 50, u.username)
                            logger.info(f"💼 [LIVE ROUTED] real broker order submitted for user {u.username} via {config.broker_name}")
                        else:
                            # Otherwise, run as PAPER / DEMO trade
                            logger.info(f"📊 [PAPER RECORDED] Demo trade saved to dashboard for user {u.username}")
                            
                    except Exception as ex:
                        logger.error(f"❌ Failed executing trade block for user {u.username}: {ex}")
                        
        except Exception as e:
            logger.error(f"❌ Multi-user routing critical failure: {e}")

if __name__ == "__main__":
    ai = GVNAiDelta60Engine()
    ai.run_ai_loop()
