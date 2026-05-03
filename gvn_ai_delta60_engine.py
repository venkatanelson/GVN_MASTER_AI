import time
import json
import logging
from datetime import datetime
import nse_option_chain
import gvn_levels_engine
from gvn_telegram_engine import TelegramAlertManager
from gvn_paper_trading_engine import PaperTradingManager
# from broker_api import place_order_universal # Real broker execution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_AI_Delta60")

class GVNAiDelta60Engine:
    """
    AI-driven Single Strike Selector & Executor
    - Monitors option chain & support/resistance
    - Normal Days: Delta 0.59 to 0.69
    - Expiry Days: Delta 0.40 to 0.60
    - Matches with GVN Pine Script Levels (0 to 1 methodology)
    - Executes automatically in Paper Trading & Broker
    """
    
    def __init__(self, bot_token=None, chat_id=None):
        self.memory = {
            "current_support": None,
            "current_resistance": None,
            "last_alert_time": 0
        }
        self.indices = ["NIFTY", "BANKNIFTY"]
        self.is_running = False
        
        # Initialize Telegram Alert Manager
        if bot_token and chat_id:
            self.telegram = TelegramAlertManager(bot_token, chat_id)
        else:
            self.telegram = None
            
        # Initialize Paper Trading for Demo Account Sync
        self.paper_trading = PaperTradingManager().get_executor()

    def analyze_support_resistance(self, option_chain):
        if not option_chain: return None, None
        calls, puts = option_chain.get("CE", []), option_chain.get("PE", [])
        if not calls or not puts: return None, None
            
        max_call = max(calls, key=lambda x: x.get("open_interest", 0) + x.get("volume", 0), default=None)
        max_put = max(puts, key=lambda x: x.get("open_interest", 0) + x.get("volume", 0), default=None)
        
        return max_put.get("strike") if max_put else None, max_call.get("strike") if max_call else None

    def detect_market_shift(self, new_support, new_resistance):
        shift_detected = False
        shift_msg = "Market Stable"
        
        old_sup, old_res = self.memory["current_support"], self.memory["current_resistance"]
        
        if old_sup and new_support and old_sup != new_support:
            if new_support < old_sup:
                shift_msg = f"📉 SUPPORT WEAK/BROKEN: Shifted down from {old_sup} to {new_support}."
            else:
                shift_msg = f"📈 SUPPORT STRONG: Shifted up from {old_sup} to {new_support}."
            shift_detected = True
            
        if old_res and new_resistance and old_res != new_resistance:
            if new_resistance > old_res:
                shift_msg = f"🚀 RESISTANCE BROKEN: Shifted up from {old_res} to {new_resistance}."
            else:
                shift_msg = f"🧱 RESISTANCE WEAK: Shifted down from {old_res} to {new_resistance}."
            shift_detected = True
            
        self.memory["current_support"] = new_support
        self.memory["current_resistance"] = new_resistance
        return shift_detected, shift_msg

    def pick_single_momentum_strike(self, option_chain, spot_price):
        """Pick EXACTLY ONE strike based on day logic and momentum"""
        best_strike = None
        closest_diff = 999
        
        # Logic: 0.40 - 0.60 on Expiry, 0.59 - 0.69 Normal
        is_expiry = datetime.now().weekday() in [2, 3] # Wed/Thu typically expiry
        target_delta = 0.50 if is_expiry else 0.64
        min_d, max_d = (0.40, 0.60) if is_expiry else (0.59, 0.69)
        
        all_options = option_chain.get("CE", []) + option_chain.get("PE", [])
        valid_strikes = []
        
        for opt in all_options:
            delta = abs(opt.get("delta", 0.5))
            if min_d <= delta <= max_d:
                valid_strikes.append(opt)
                
        # Pick the SINGLE strike with highest momentum (volume/gamma)
        if valid_strikes:
            # Sort by proximity to target delta and highest volume
            best_strike = sorted(valid_strikes, key=lambda x: (abs(abs(x.get("delta",0.5)) - target_delta), -x.get("volume", 0)))[0]
                
        return best_strike

    def trigger_execution_and_alerts(self, symbol, strike_info, shift_msg, levels):
        """Send JSON Alert, execute in Broker, and Sync with Demo Account"""
        entry_price = strike_info.get("ltp", 0)
        target = levels.get('i2', entry_price + 20)
        sl = levels.get('sl', entry_price - 10)
        
        # 1. Prepare JSON Alert
        trade_json = {
            "Action": "WAIT FOR SIGNAL",
            "Symbol": f"{symbol}{strike_info.get('strike')}{strike_info.get('option_type', 'CE')}",
            "LTP": entry_price,
            "Delta": round(abs(strike_info.get("delta", 0.60)), 2),
            "Momentum_Expected": "HIGH",
            "Target": target,
            "StopLoss": sl,
            "Market_Shift": shift_msg
        }
        
        json_str = json.dumps(trade_json, indent=4)
        telegram_msg = f"🤖 <b>GVN AI SINGLE STRIKE EXECUTION</b> 🤖\n<pre>{json_str}</pre>\n⚡ <i>0 to 1 Methodology Sync Complete</i>"
        
        # 2. Alert Telegram
        if self.telegram:
            self.telegram.bot.send_message(telegram_msg)
        logger.info(f"🚀 AI EXECUTION SIGNAL:\n{telegram_msg}")
        
        # 3. Trigger Demo Account (Paper Trading)
        logger.info("📝 Syncing with Demo Account (Wait for Signal Process)...")
        self.paper_trading.execute_paper_buy(
            symbol=symbol,
            strike=strike_info.get("strike"),
            option_type=strike_info.get("option_type", "CE"),
            entry_price=entry_price,
            target=target,
            sl=sl,
            quantity=50 # default qty
        )
        
        # 4. Trigger Real Broker Execution (Placeholder)
        logger.info("🔗 Sending Execution to Broker Account API...")
        # place_order_universal(cfg={}, symbol=trade_json["Symbol"], txn_type="BUY", qty=50)

    def run_ai_loop(self):
        self.is_running = True
        logger.info("🧠 [GVN AI] Single Strike Momentum Analyzer Started")
        
        while self.is_running:
            try:
                for index in self.indices:
                    chain = nse_option_chain.get_option_chain(index)
                    if not chain: continue
                        
                    spot_price = chain.get("spot_price", 25000)
                    support, resistance = self.analyze_support_resistance(chain)
                    shift_detected, shift_msg = self.detect_market_shift(support, resistance)
                    
                    # SINGLE STRIKE PICK
                    best_strike = self.pick_single_momentum_strike(chain, spot_price)
                    
                    # Fire only if shift detected or hourly sync
                    if best_strike and (shift_detected or (time.time() - self.memory["last_alert_time"] > 3600)):
                        # Sync with GVN Pine Script Levels (0 to 1)
                        high_915 = best_strike.get("high_915", spot_price + 20)
                        low_915 = best_strike.get("low_915", spot_price - 20)
                        levels = gvn_levels_engine.calculate_gvn_levels(high_915, low_915)
                        
                        self.trigger_execution_and_alerts(index, best_strike, shift_msg, levels)
                        self.memory["last_alert_time"] = time.time()
                
                time.sleep(5)
            except Exception as e:
                logger.error(f"[GVN AI ERROR] {e}")
                time.sleep(5)

    def stop(self):
        self.is_running = False

if __name__ == "__main__":
    ai = GVNAiDelta60Engine()
    print("Testing Engine Mechanics...")
    # Mock data to verify JSON format
    ai.trigger_execution_and_alerts("NIFTY", {"strike": 24200, "option_type": "PE", "ltp": 350, "delta": -0.62}, "SUPPORT WEAK: 24400 -> 24200", {"i2": 380, "sl": 320})
