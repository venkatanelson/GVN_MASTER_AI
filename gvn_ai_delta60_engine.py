
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
                    strikes = self._pick_alpha_strikes(records, spot)
                    
                    # 📸 PERIODIC SNAPSHOT (Every 5 minutes)
                    if time.time() - self.last_snapshot_time > 300:
                        self._save_market_snapshot(index, strikes)
                        self.last_snapshot_time = time.time()

                    for strike in strikes:
                        self._manage_trade_cycle(index, strike)
                
                time.sleep(2)
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

    def _pick_alpha_strikes(self, records, spot):
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
                            "low_915": opt.get("low_915", opt.get("lastPrice", 0) - 15)
                        })
        return sorted(alpha_grid, key=lambda x: abs(x["delta"] - target_d))[:14]

    def _manage_trade_cycle(self, symbol, strike):
        key = f"{strike['strike']}_{strike['type']}"
        ltp = strike["ltp"]
        levels = gvn_levels_engine.calculate_gvn_levels(strike["high_915"], strike["low_915"])
        if not levels: return
        
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

            # 🎯 GVN PROBABILITY & PRIORITY LEVEL DETECTION
            hit_level_name = None
            target_price = None
            priority = None

            def is_near(price, level):
                return level > 0 and (level * 0.98 <= price <= level * 1.02)

            # Priority 1: i5 Level (50% Level)
            if is_near(ltp, levels["i5"]):
                hit_level_name, target_price, priority = "i5 (Priority 1: 50% Level)", levels["i3"], 1
            # Priority 2: i7 Level
            elif is_near(ltp, levels["i7"]):
                hit_level_name, target_price, priority = "i7 (Priority 2)", levels["i5"], 2
            # Priority 3: i1 / i0 Level (Bottom Bounce - Huge Target to i5)
            elif is_near(ltp, levels.get("i1", 0)) or is_near(ltp, levels.get("i0", 0)):
                hit_level_name, target_price, priority = "i1/i0 (Priority 3: Bottom Reversal)", levels["i5"], 3
            # Priority Gap Up/Down: i6 Level
            elif is_near(ltp, levels["i6"]) and ("GAP" in wind_dir or ltp > strike["high_915"] * 1.05 or ltp < strike["low_915"] * 0.95):
                hit_level_name, target_price, priority = "i6 (Priority Gap Zone)", levels["i3"], 4

            if hit_level_name:
                alert_key = f"{key}_{hit_level_name}"
                if alert_key not in self.memory["alerted_levels"]:
                    # Create Alert on Touch!
                    alert_msg = f"🔔 <b>GVN LEVEL ALERT</b> 🔔\n{symbol} {strike['strike']} {strike['type']} touched <b>{hit_level_name}</b> @ {ltp}\nTarget Probability: {target_price}"
                    if self.telegram: self.telegram.send_alert(alert_msg)
                    self.memory["alerted_levels"][alert_key] = True

                # If Wind Direction supports the probability, execute!
                if is_bullish or is_bearish:
                    self._execute_smart_entry(symbol, strike, ltp, levels, priority)
        else:
            trade = self.memory["active_trades"][key]
            
            # 🌪️ WIND DIRECTION REVERSAL EXIT
            wind_dir = shared_data.market_pulse.get("wind_direction", "UNKNOWN")
            is_wind_against = (strike["type"] == "CE" and any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING"])) or \
                              (strike["type"] == "PE" and any(w in wind_dir for w in ["UP WIND", "SHORT COVERING"]))
            
            if is_wind_against:
                remaining = trade["total_lots"] - (trade["total_lots"] // 2 if trade["t1_hit"] else 0)
                if remaining > 0:
                    self._fire_order(symbol, strike, "SELL", remaining, "Full Exit (Wind Reversal)")
                del self.memory["active_trades"][key]
                return

            # 📈 LEVEL-BASED TRAILING STOP LOSS (TSL)
            # Find the highest GVN level crossed by the LTP
            highest_crossed = max([lvl for lvl in levels.values() if lvl <= ltp], default=0)
            
            if highest_crossed > trade.get("highest_level", 0) and highest_crossed > trade["entry"]:
                trade["highest_level"] = highest_crossed
                new_sl = highest_crossed - 12
                # Only trail upwards
                if new_sl > trade["sl"]:
                    trade["sl"] = new_sl
                    if self.telegram:
                        self.telegram.send_alert(f"📈 <b>GVN TSL TRAILED</b>\n{symbol} {strike['strike']} {strike['type']} crossed {highest_crossed}\nNew SL: {new_sl}")

            # Multi-Stage Exit
            if not trade["t1_hit"] and ltp >= trade["t1"]:
                trade["t1_hit"] = True
                self._fire_order(symbol, strike, "SELL", trade["total_lots"] // 2, "Partial Exit (T1 Hit)")
            elif ltp >= trade["t2"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"] - (trade["total_lots"] // 2 if trade["t1_hit"] else 0), "Full Exit (T2 Hit)")
                del self.memory["active_trades"][key]
            # Stop Loss / Trailing Stop Loss Exit
            elif ltp <= trade["sl"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"] - (trade["total_lots"] // 2 if trade["t1_hit"] else 0), "Full Exit (SL Hit)")
                del self.memory["active_trades"][key]

    def _execute_smart_entry(self, symbol, strike, price, levels, priority):
        balance = shared_data.market_data.get("available_cash", 20000)
        target_lots = max(1, min(5, int(balance / 10000)))
        key = f"{strike['strike']}_{strike['type']}"
        
        # We use the custom probability target defined by the priority engine (like i1 bouncing to i5)
        if priority == 3: # i1 / i0 hit (Zero to Hero)
            t1, t2 = levels.get("i7", price + 15), levels.get("i5", price + 30)
        elif priority == 2: # i7 hit
            t1, t2 = levels.get("i6", price + 10), levels.get("i5", price + 20)
        elif priority == 1: # i5 hit
            t1, t2 = levels.get("i3", price + 20), levels.get("i2", price + 40)
        else:
            t1, t2 = levels.get("i3", price + 15), levels.get("i2", price + 30)
        
        # 🛡️ USER REQUESTED EXACTLY 12-POINT FIXED STOP LOSS
        sl = price - 12
        
        wind_dir = shared_data.market_pulse.get("wind_direction", "UNKNOWN")
        reason = f"Smart Priority Entry | Wind: {wind_dir} | SL: 12pts"
        
        self.memory["active_trades"][key] = {"entry": price, "t1": t1, "t2": t2, "sl": sl, "t1_hit": False, "total_lots": target_lots}
        self._fire_order(symbol, strike, "BUY", target_lots, reason)
        self.paper_trading.execute_paper_buy(symbol, strike["strike"], strike["type"], price, t2, sl)

    def _fire_order(self, symbol, strike, side, qty, reason):
        full_symbol = f"{symbol}{strike['strike']}{strike['type']}"
        alert = f"🛡️ <b>GVN SAFETY EXECUTION</b> 🛡️\n{full_symbol} {side} @ {strike['ltp']}\nQty: {qty} Lots\nReason: {reason}"
        if self.telegram: self.telegram.send_alert(alert)
        cfg = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel", {})
        place_order_universal(cfg, full_symbol, side, qty * 50)

if __name__ == "__main__":
    ai = GVNAiDelta60Engine()
    ai.run_ai_loop()
