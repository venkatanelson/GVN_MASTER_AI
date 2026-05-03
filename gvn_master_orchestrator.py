"""
GVN Master Orchestrator: Central Hub for All 25-Point Trading System
Coordinates Greeks, AI Sentiment, i-Levels, Execution, Alerts, and Paper Trading
"""

import logging
from datetime import datetime
import json
from typing import Dict, Any, Optional

# Import all engines
try:
    from gvn_greeks_engine import AlphaGridMonitor, StrikeSelector
    from gvn_ai_sentiment_engine import UnifiedSentimentFilter
    from gvn_levels_engine import calculate_gvn_levels, TradeSetupGenerator, is_expiry_day
    from gvn_telegram_engine import TelegramAlertManager
    from gvn_paper_trading_engine import PaperTradingManager
    from gvn_webhook_executor import WebhookExecutor, TradeOrderFormatter
    from broker_api import shoonya_http_login, dhan_http_test, angel_http_login
    from gvn_live_execution_engine import GVNLiveExecutionEngine
    from gvn_ai_delta60_engine import GVNAiDelta60Engine
except ImportError as e:
    print(f"⚠️ Warning: Some engines could not be imported: {e}")

import shared_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterOrchestrator")

class GVNMasterOrchestrator:
    def __init__(self, broker_config: Dict[str, Any] = None, telegram_config: Dict[str, Any] = None):
        self.broker_config = broker_config if broker_config is not None else {}
        self.telegram_config = telegram_config if telegram_config is not None else {}
        
        logger.info("🚀 Initializing GVN Master Orchestrator...")
        
        try:
            self.greeks_monitor = AlphaGridMonitor(self.broker_config)
            self.strike_selector = StrikeSelector()
            self.sentiment_filter = UnifiedSentimentFilter()
            self.telegram_manager = TelegramAlertManager(
                self.telegram_config.get("bot_token", ""),
                self.telegram_config.get("chat_id", "")
            )
            self.paper_trading = PaperTradingManager()
            self.webhook_executor = WebhookExecutor(
                webhook_url=self.broker_config.get("webhook_url"),
                broker=self.broker_config.get("broker_name", "Dhan")
            )
            # Initialize Live Execution Engine
            self.live_executor = GVNLiveExecutionEngine(
                broker_api=None,  # Will attach broker instance later
                telegram_bot_token=self.telegram_config.get("bot_token", ""),
                telegram_chat_id=self.telegram_config.get("chat_id", "")
            )
            # Initialize AI Delta 60 Engine
            self.ai_delta60_engine = GVNAiDelta60Engine(
                bot_token=self.telegram_config.get("bot_token", ""),
                chat_id=self.telegram_config.get("chat_id", "")
            )
        except Exception as e:
            logger.error(f"❌ Error initializing engines: {e}")
        
        self.active_trades = []
        self.is_live_mode = False
        self.system_initialized = False
        self.gvn_levels = None
        self.current_sentiment = None

    def start(self, config: Dict[str, Any] = None):
        if config:
            self.broker_config.update(config)
            
        logger.info("📋 Initializing system components...")
        
        broker = self.broker_config.get("broker_name", "").lower()
        
        if "shoonya" in broker:
            try:
                token = shoonya_http_login(self.broker_config)
                if token:
                    self.broker_config["session_token"] = token
                    shared_data.broker_connection_status["Shoonya"] = True
                    self.telegram_manager.alert_status("CONNECTED", "✅ Shoonya Connected")
                    logger.info("✅ Shoonya authenticated")
                else:
                    shared_data.broker_connection_status["Shoonya"] = False
                    self.telegram_manager.alert_status("DISCONNECTED", "❌ Shoonya auth failed")
                    logger.error("❌ Shoonya authentication failed")
            except Exception as e:
                shared_data.broker_connection_status["Shoonya"] = False
                logger.error(f"❌ Shoonya Login Error: {e}")
                
        elif "angel" in broker:
            try:
                token = angel_http_login(self.broker_config)
                if token:
                    self.broker_config["session_token"] = token
                    shared_data.broker_connection_status["AngelOne"] = True
                    self.telegram_manager.alert_status("CONNECTED", "✅ Angel One Connected")
                    logger.info("✅ Angel One authenticated")
                else:
                    shared_data.broker_connection_status["AngelOne"] = False
                    self.telegram_manager.alert_status("DISCONNECTED", "❌ Angel One auth failed")
                    logger.error("❌ Angel One authentication failed")
            except Exception as e:
                shared_data.broker_connection_status["AngelOne"] = False
                logger.error(f"❌ Angel One Login Error: {e}")
        
        import threading
        if hasattr(self, 'ai_delta60_engine'):
            threading.Thread(target=self.ai_delta60_engine.run_ai_loop, daemon=True).start()
            logger.info("🧠 AI Delta 60 Engine background loop started.")

        self.system_initialized = True
        shared_data.system_status["initialized"] = True
        logger.info("✅ System initialization complete")

    def on_market_tick(self, symbol: str, spot_price: float, volume: int, open_interest: int):
        shared_data.update_market_data(symbol, spot_price)
        # Logic for tick processing...
        pass

# Singleton pattern
_orchestrator = None

def get_orchestrator(broker_config=None, telegram_config=None):
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = GVNMasterOrchestrator(broker_config, telegram_config)
    elif broker_config:
        _orchestrator.broker_config.update(broker_config)
    return _orchestrator
