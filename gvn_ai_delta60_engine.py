
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

        if key not in self.memory["active_trades"]:
            if (ltp <= levels["i7"] * 1.01 or (ltp >= levels["i5"] and ltp <= levels["i5"] * 1.03)) \
               and shared_data.market_pulse["score"] >= 65:
                self._execute_smart_entry(symbol, strike, ltp, levels)
        else:
            trade = self.memory["active_trades"][key]
            # Multi-Stage Exit
            if not trade["t1_hit"] and ltp >= trade["t1"]:
                trade["t1_hit"], trade["sl"] = True, trade["entry"]
                self._fire_order(symbol, strike, "SELL", trade["total_lots"] // 2, "Partial Exit (T1 Hit)")
            elif ltp >= trade["t2"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"] - (trade["total_lots"] // 2 if trade["t1_hit"] else 0), "Full Exit (T2 Hit)")
                del self.memory["active_trades"][key]
            elif ltp <= trade["sl"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"] - (trade["total_lots"] // 2 if trade["t1_hit"] else 0), "Full Exit (SL Hit)")
                del self.memory["active_trades"][key]

    def _execute_smart_entry(self, symbol, strike, price, levels):
        balance = shared_data.market_data.get("available_cash", 20000)
        target_lots = max(1, min(5, int(balance / 10000)))
        key = f"{strike['strike']}_{strike['type']}"
        t1 = levels["i6"] if price < levels["i5"] else levels["i3"]
        t2 = levels["i5"] if price < levels["i5"] else levels["i2"]
        sl = levels["i7"] * 0.95
        self.memory["active_trades"][key] = {"entry": price, "t1": t1, "t2": t2, "sl": sl, "t1_hit": False, "total_lots": target_lots}
        self._fire_order(symbol, strike, "BUY", target_lots, f"Smart Entry ({target_lots} Lots)")
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
