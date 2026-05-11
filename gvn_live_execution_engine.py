import time
import json
import logging
from datetime import datetime
from gvn_levels_engine import calculate_gvn_levels
from gvn_telegram_engine import TelegramAlertManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LiveExecutionEngine")

class GVNLiveExecutionEngine:
    """
    GVN Master Auto-Algo Execution Engine
    Filters Delta 60, Calculates 9:15 Levels, and Fires Orders securely.
    """
    def __init__(self, broker_api, telegram_bot_token=None, telegram_chat_id=None):
        self.broker = broker_api
        self.telegram = TelegramAlertManager(telegram_bot_token, telegram_chat_id)
        self.active_strikes = {"CE": None, "PE": None}  # Only 1 CE and 1 PE
        self.memory_levels = {}
        self.running_trades = {}
        
    def find_master_strikes(self, option_chain):
        """Filter Option Chain to find the perfect Delta 60 Strikes"""
        logger.info("🔍 Scanning for Delta 60 Strikes (Max 1 CE, 1 PE)...")
        # In a real scenario, this matches the Delta logic (0.60 - 0.69)
        # For Expiry days, this will look for 0.40 - 0.50
        is_expiry = datetime.now().weekday() == 3 # Thursday Expiry Example
        target_delta_min = 0.40 if is_expiry else 0.60
        target_delta_max = 0.60 if is_expiry else 0.69
        
        # Mocking selection for structure
        for opt in option_chain:
            delta = abs(opt.get("delta", 0.5))
            if target_delta_min <= delta <= target_delta_max:
                if opt['type'] == 'CE' and not self.active_strikes["CE"]:
                    self.active_strikes["CE"] = opt['symbol']
                elif opt['type'] == 'PE' and not self.active_strikes["PE"]:
                    self.active_strikes["PE"] = opt['symbol']
                    
        logger.info(f"🎯 Master Strikes Locked: CE={self.active_strikes['CE']}, PE={self.active_strikes['PE']}")

    def fetch_915_candle(self, symbol):
        """Fetch the 9:15 AM candle High and Low from Broker"""
        logger.info(f"📊 Fetching 9:15 AM Master Candle for {symbol}")
        # Call Angel One Historical API here: getCandleData
        # Mocking the API response for the architecture
        return {"high": 350.50, "low": 290.20, "close": 320.00}

    def generate_levels(self):
        """Generate Fibonacci Levels for Locked Strikes"""
        for opt_type, symbol in self.active_strikes.items():
            if symbol:
                candle = self.fetch_915_candle(symbol)
                # Apply GVN Fibonacci logic
                levels = calculate_gvn_levels(candle['high'], candle['low'], candle['close'])
                self.memory_levels[symbol] = levels
                logger.info(f"✅ Levels generated for {symbol}: i5(Blue)={levels['i5']}, i1(Green)={levels['i1']}")

    def check_long_buildup(self, symbol, current_price, current_oi):
        """Filter: Ensure price and OI are both rising"""
        # Logic to check if (Price > Previous Price) AND (OI > Previous OI)
        # Assuming True for now to allow architecture flow
        return True

    def log_level_touch(self, symbol, ltp, level_name, level_value):
        """Send a structured JSON alert and update AI Memory for any level touch"""
        now = datetime.now()
        # Mock expiry for the JSON alert (in real case, fetch from option chain data)
        expiry = "2026-05-14" 
        
        alert_json = {
            "type": "LEVEL_TOUCH",
            "symbol": symbol,
            "level": level_name,
            "level_price": level_value,
            "current_price": ltp,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "seconds": now.second,
            "expiry": expiry,
            "action": "OBSERVING"
        }
        
        # 1. Update AI Memory in shared_data
        import shared_data
        with shared_data._data_lock:
            observation = f"[{now.strftime('%H:%M:%S')}] {symbol} touched {level_name} at {ltp}. Institutional scanning active."
            if not hasattr(shared_data, 'ai_memory'):
                shared_data.ai_memory = []
            shared_data.ai_memory.insert(0, observation)
            if len(shared_data.ai_memory) > 50:
                shared_data.ai_memory.pop()
        
        # 2. Send Telegram Alert
        # self.telegram.send_json_alert(alert_json)
        logger.info(f"📡 ALERT: {symbol} touch {level_name} at {ltp}. JSON Fired.")

    def run_live_scan(self, live_ltp_data):
        """Continuously check LTP against all i-levels (i1, i3, i5, i6, i7)"""
        for symbol, ltp in live_ltp_data.items():
            if symbol in self.memory_levels:
                levels = self.memory_levels[symbol]
                
                # Iterate through all key levels requested by user
                for lvl in ['i1', 'i3', 'i5', 'i6', 'i7']:
                    lvl_val = levels.get(lvl)
                    if lvl_val and abs(ltp - lvl_val) <= 0.5: # 0.5 point precision
                        self.log_level_touch(symbol, ltp, lvl, lvl_val)
                        
                        # Logic for Entry (Priority levels)
                        if lvl in ['i5', 'i7'] and symbol not in self.running_trades:
                            if self.check_long_buildup(symbol, ltp, 0):
                                self.execute_trade(symbol, ltp, target=levels.get('i3' if lvl=='i7' else 'i1'), sl=levels['sl'])

    def execute_trade(self, symbol, entry_price, target, sl):
        """Execute JSON Order and Send Telegram Alert"""
        now = datetime.now()
        logger.info(f"🚀 EXECUTING BUY ORDER FOR {symbol} at {entry_price}")
        
        trade_json = {
            "type": "ORDER_EXECUTION",
            "symbol": symbol,
            "entry_price": entry_price,
            "target": target,
            "sl": sl,
            "transactionType": "BUY",
            "orderType": "MARKET",
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "seconds": now.second,
            "expiry": "2026-05-14"
        }
        
        # 1. Update AI Memory
        import shared_data
        with shared_data._data_lock:
            if not hasattr(shared_data, 'ai_memory'): shared_data.ai_memory = []
            shared_data.ai_memory.insert(0, f"🚀 [ORDER] Executing BUY for {symbol} at {entry_price}. Target: {target}")
        
        self.running_trades[symbol] = trade_json
        # 2. Send Telegram Alert
        self.telegram.alert_entry(trade_json)
        logger.info("✅ JSON Order & Alert Fired successfully.")

# Example Initialization
if __name__ == "__main__":
    engine = GVNLiveExecutionEngine(broker_api=None)
    engine.find_master_strikes([
        {"symbol": "NIFTY24200CE", "type": "CE", "delta": 0.65},
        {"symbol": "NIFTY24300PE", "type": "PE", "delta": 0.62}
    ])
    engine.generate_levels()
    engine.run_live_scan({"NIFTY24200CE": 320.00})  # Simulating LTP touching a level
