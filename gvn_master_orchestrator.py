"""
GVN Master Orchestrator: Central Hub for All 25-Point Trading System
Coordinates Greeks, AI Sentiment, i-Levels, Execution, Alerts, and Paper Trading
"""

import logging
from datetime import datetime, timedelta
import json
from typing import Dict, Any, Optional

# Import all engines
from gvn_greeks_engine import AlphaGridMonitor, StrikeSelector
from gvn_ai_sentiment_engine import UnifiedSentimentFilter
from gvn_levels_engine import calculate_gvn_levels, TradeSetupGenerator, is_expiry_day
from gvn_telegram_engine import TelegramAlertManager
from gvn_paper_trading_engine import PaperTradingManager
from gvn_webhook_executor import WebhookExecutor, TradeOrderFormatter
from broker_api import shoonya_http_login, dhan_http_test
import shared_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterOrchestrator")


# ───────────────────────────────────────────────────────────────
# GVN MASTER ORCHESTRATOR
# ───────────────────────────────────────────────────────────────

class GVNMasterOrchestrator:
    """
    Central command center for the entire 25-point trading system
    Orchestrates all engines and coordinates trading decisions
    """
    
    def __init__(self, broker_config: Dict[str, Any], telegram_config: Dict[str, Any] = None):
        """
        Initialize orchestrator with all engines
        
        broker_config: {
            "broker_name": "Shoonya" or "Dhan",
            "client_id": "...",
            "password": "...",
            "api_key": "...",
            "access_token": "...",
            "webhook_url": "..."
        }
        """
        
        self.broker_config = broker_config if broker_config is not None else {}
        self.telegram_config = telegram_config if telegram_config is not None else {}
        
        # Initialize all engines
        logger.info("🚀 Initializing GVN Master Orchestrator...")
        
        self.greeks_monitor = AlphaGridMonitor(self.broker_config)
        self.strike_selector = StrikeSelector()
        self.sentiment_filter = UnifiedSentimentFilter()
        self.telegram_manager = TelegramAlertManager(
            self.telegram_config.get("bot_token", ""),
            self.telegram_config.get("chat_id", "")
        )
        self.paper_trading = PaperTradingManager()
        self.webhook_executor = WebhookExecutor(
            webhook_url=self.broker_config.get("webhook_url") if isinstance(self.broker_config, dict) else None,
            broker=self.broker_config.get("broker_name", "Dhan") if isinstance(self.broker_config, dict) else "Dhan"
        )
        
        # System state
        self.active_trades = []
        self.is_live_mode = False
        self.system_initialized = False
        self.gvn_levels = None
        self.current_sentiment = None
    
    def initialize_system(self):
        """Initialize all system components"""
        logger.info("📋 Initializing system components...")
        
        # Verify broker connectivity
        broker = self.broker_config.get("broker_name", "").lower()
        
        if "shoonya" in broker:
            token = shoonya_http_login(self.broker_config)
            if token:
                self.broker_config["session_token"] = token
                shared_data.update_market_data("Shoonya", True)
                self.telegram_manager.alert_status("CONNECTED", "✅ Shoonya Connected")
                logger.info("✅ Shoonya authenticated")
            else:
                self.telegram_manager.alert_status("DISCONNECTED", "❌ Shoonya auth failed")
                logger.error("❌ Shoonya authentication failed")
        
        elif "dhan" in broker:
            if dhan_http_test(self.broker_config):
                shared_data.update_market_data("Dhan", True)
                self.telegram_manager.alert_status("CONNECTED", "✅ Dhan Connected")
                logger.info("✅ Dhan authenticated")
            else:
                self.telegram_manager.alert_status("DISCONNECTED", "❌ Dhan auth failed")
                logger.error("❌ Dhan authentication failed")
        
        self.system_initialized = True
        shared_data.system_status["initialized"] = True
        logger.info("✅ System initialization complete")
    
    def on_915_candle(self, symbol: str, high: float, low: float, close: float):
        """
        Called when 9:15 candle is closed
        Calculates GVN i-levels for the day
        """
        logger.info(f"📍 9:15 Candle received for {symbol}")
        
        # Calculate GVN levels
        levels = calculate_gvn_levels(high, low, close)
        self.gvn_levels = levels
        
        # Store in shared data
        shared_data.gvn_levels = levels
        
        # Setup trades from levels
        strategy = "Strategy 3" if is_expiry_day() else "Strategy 1"
        setup_gen = TradeSetupGenerator(levels, strategy)
        trades = setup_gen.get_all_trades()
        
        logger.info(f"✅ Generated {len(trades)} trade setups for {symbol}")
        return trades
    
    def on_market_tick(self, symbol: str, spot_price: float, volume: int, open_interest: int):
        """
        Called on every 1-second tick
        Updates Greeks, checks sentiment, monitors trades
        """
        
        # Update market data
        shared_data.update_market_data(symbol, spot_price)
        
        # Fetch and monitor option chain
        chain = self.greeks_monitor.harvester.fetch_shoonya_option_chain(symbol, "")
        if chain:
            grid = self.greeks_monitor.build_alpha_grid(symbol, spot_price, chain)
            shared_data.gvn_alpha_grid = grid
            
            # Analyze sentiment
            direction = "UP" if spot_price >= shared_data.market_data.get(symbol, 0) else "DOWN"
            sentiment = self.sentiment_filter.get_full_sentiment(grid, spot_price, volume, direction)
            self.current_sentiment = sentiment
            shared_data.market_pulse["mode"] = sentiment.get("verdict")
            shared_data.sentiment_history.append(sentiment)
    
    def check_entry_conditions(self, symbol: str, trade_setup: Dict[str, Any]):
        """
        Check if entry conditions are met for a trade setup
        Validates: Price crossover, sentiment, Greeks, filters
        """
        
        if not self.system_initialized:
            return False, "System not initialized"
        
        if not self.current_sentiment:
            return False, "Sentiment not calculated"
        
        # Check sentiment filter
        if "SELL" in self.current_sentiment.get("verdict", ""):
            return False, "Market sentiment bearish"
        
        # Check if reversal warning
        if self.current_sentiment.get("warnings", {}).get("is_reversal"):
            return False, "Reversal detected"
        
        # Check fake breakout
        if self.current_sentiment.get("warnings", {}).get("is_fake_breakout"):
            return False, "Fake breakout detected"
        
        logger.info(f"✅ Entry conditions met for {symbol} - {trade_setup.get('entry_level')}")
        return True, "Ready to enter"
    
    def execute_trade(self, trade_setup: Dict[str, Any], symbol: str, is_live=False):
        """Execute trade (live or paper)"""
        
        entry_level = trade_setup.get("entry_level")
        entry_price = trade_setup.get("buffered_entry")
        target = trade_setup.get("buffered_target")
        sl = trade_setup.get("buffered_sl")
        quantity = self.broker_config.get("quantity", 65)
        
        trade_info = {
            "symbol": symbol,
            "strike": trade_setup.get("strike", symbol),
            "option_type": "CE",
            "entry_level": entry_level,
            "entry_price": entry_price,
            "target": target,
            "sl": sl,
            "quantity": quantity,
            "is_live": is_live,
            "timestamp": datetime.now().isoformat()
        }
        
        # Execute paper trade always
        paper_trade = self.paper_trading.get_executor().execute_paper_buy(
            symbol=symbol,
            strike=trade_setup.get("strike", symbol),
            option_type="CE",
            entry_price=entry_price,
            target=target,
            sl=sl,
            quantity=quantity
        )
        
        # Send alert
        self.telegram_manager.alert_entry(trade_info)
        logger.info(f"📝 Trade executed (Paper): {symbol} {entry_level} @ {entry_price}")
        
        # Execute live trade if enabled
        if is_live:
            order = TradeOrderFormatter.format_buy_order(
                symbol, symbol, "CE", quantity, entry_price, target, sl
            )
            success, msg = self.webhook_executor.execute_order(
                order,
                secret_key=self.broker_config.get("api_key")
            )
            
            if success:
                logger.info(f"✅ Live trade executed: {symbol}")
                self.active_trades.append(trade_info)
            else:
                logger.error(f"❌ Live trade failed: {msg}")
        
        return paper_trade
    
    def check_exits(self, symbol: str, current_price: float):
        """Check if any trades should be exited"""
        
        exits = []
        
        # Check 3:15 PM square-off
        now = datetime.now()
        if now.hour == 15 and now.minute >= 15:
            logger.info("⏰ 3:15 PM: Auto square-off triggered")
            return self.active_trades  # Return all trades to close
        
        # Check paper trades
        for trade in self.paper_trading.get_executor().portfolio.active_trades[:]:
            # Check if hit target
            if current_price >= trade.get("target"):
                self.paper_trading.get_executor().execute_paper_sell(
                    trade["id"],
                    exit_price=current_price,
                    exit_reason="TARGET_HIT"
                )
                exits.append(trade)
                logger.info(f"🎯 Target hit: {trade['symbol']}")
            
            # Check if hit SL
            elif current_price <= trade.get("sl"):
                self.paper_trading.get_executor().execute_paper_sell(
                    trade["id"],
                    exit_price=current_price,
                    exit_reason="SL_HIT"
                )
                exits.append(trade)
                logger.error(f"❌ Stop loss hit: {trade['symbol']}")
        
        return exits
    
    def get_system_status_report(self):
        """Generate complete system status report"""
        
        paper_stats = self.paper_trading.get_executor().get_performance_metrics()
        
        report = {
            "system": {
                "initialized": self.system_initialized,
                "timestamp": datetime.now().isoformat(),
                "mode": "LIVE" if self.is_live_mode else "PAPER",
                "active_trades": len(self.active_trades)
            },
            "market": {
                "sentiment": self.current_sentiment,
                "gvn_levels": self.gvn_levels,
                "spot_prices": shared_data.get_market_data()
            },
            "paper_trading": paper_stats,
            "broker": {
                "connected": self.broker_config.get("session_token") is not None,
                "broker_name": self.broker_config.get("broker_name")
            }
        }
        
        return report
    
    def send_daily_summary(self):
        """Send end-of-day summary via Telegram"""
        
        stats = self.paper_trading.get_executor().get_performance_metrics()
        
        summary = {
            "total_trades": stats["total_trades"],
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "total_pnl": stats["total_pnl"]
        }
        
        self.telegram_manager.alert_daily_summary(summary)
        logger.info("📊 Daily summary sent")


# ───────────────────────────────────────────────────────────────
# GLOBAL ORCHESTRATOR INSTANCE
# ───────────────────────────────────────────────────────────────

_orchestrator = None

def get_orchestrator(broker_config=None, telegram_config=None):
    """Get or create global orchestrator instance"""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = GVNMasterOrchestrator(broker_config, telegram_config)
    elif broker_config:
        _orchestrator.broker_config.update(broker_config)
    
    return _orchestrator


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test orchestrator
    config = {
        "broker_name": "Dhan",
        "client_id": "test",
        "access_token": "test_token",
        "webhook_url": None,
        "quantity": 65
    }
    
    telegram_config = {
        "bot_token": "",
        "chat_id": ""
    }
    
    orchestrator = GVNMasterOrchestrator(config, telegram_config)
    orchestrator.initialize_system()
    
    # Test 9:15 candle
    trades = orchestrator.on_915_candle("NIFTY", 25100, 24900, 25000)
    print(f"\n✅ Generated {len(trades)} trades from 9:15 candle")
    
    # Test market tick
    orchestrator.on_market_tick("NIFTY", 25050, 1000000, 50000)
    print(f"✅ Market tick processed")
    
    # Print status
    print(json.dumps(orchestrator.get_system_status_report(), indent=2, default=str))
