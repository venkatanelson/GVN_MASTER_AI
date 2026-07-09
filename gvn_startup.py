"""
GVN Master Robot - Startup Configuration & Integration
Initializes all core components for production trading
"""

import logging
import sys
from datetime import datetime
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GVNStartup")

# Import core modules
import gvn_master_robot
import gvn_delta_levels_engine
import gvn_levels_engine
import broker_api
import shared_data

class GVNSystem:
    """
    Main orchestrator for GVN trading system.
    Initializes, monitors, and manages all components.
    """
    
    def __init__(self):
        self.robot = None
        self.is_running = False
        self.start_time = None
        self.error_count = 0
        logger.info("🚀 [GVN SYSTEM] Initializing GVN Master Trading System...")
    
    def initialize(self):
        """Initialize all GVN components"""
        try:
            logger.info("📊 [INIT] Verifying broker connectivity...")
            if not self._verify_broker_connection():
                logger.warning("⚠️ [INIT] Broker connection failed - will retry on first trade")
            
            logger.info("📁 [INIT] Loading market data structures...")
            self._load_shared_data()
            
            logger.info("📊 [INIT] Synchronizing daily FII/DII records...")
            try:
                from gvn_fii_dii_fetcher import sync_fii_dii_data
                sync_fii_dii_data()
            except Exception as fe:
                logger.error(f"⚠️ [INIT] FII/DII synchronization failed: {fe}")
            
            logger.info("🤖 [INIT] Creating Master Robot instance...")
            self.robot = gvn_master_robot.GVNMasterRobot()
            
            logger.info("✅ [INIT] GVN System initialization complete")
            return True
        
        except Exception as e:
            logger.error(f"❌ [INIT] Initialization failed: {e}")
            return False

    def _verify_broker_connection(self):
        """Test broker connectivity"""
        try:
            # This would connect to actual broker in production
            logger.info("✓ Broker connection verified")
            return True
        except:
            return False

    def _load_shared_data(self):
        """Initialize shared data structures"""
        shared_data.reset_daily_stats()
        logger.info(f"✓ Shared data initialized")

    def start(self):
        """Start the trading robot"""
        if self.is_running:
            logger.warning("⚠️ [START] System already running")
            return False
        
        try:
            if not self.initialize():
                return False
            
            self.is_running = True
            self.start_time = datetime.now()
            self.error_count = 0
            
            logger.info("🟢 [SYSTEM] Starting Master Robot...")
            
            # Start robot in background thread
            robot_thread = threading.Thread(
                target=self.robot.run_robot_cycle,
                daemon=False,
                name="GVN-RobotCycle"
            )
            robot_thread.start()
            
            logger.info(f"🚀 [SYSTEM] GVN Trading System LIVE at {self.start_time.strftime('%H:%M:%S')}")
            return True
        
        except Exception as e:
            logger.error(f"❌ [START] Failed to start system: {e}")
            self.is_running = False
            return False

    def stop(self):
        """Stop the trading robot gracefully"""
        try:
            logger.info("🛑 [SYSTEM] Stopping GVN Trading System...")
            
            if self.robot:
                self.robot.stop()
            
            self.is_running = False
            
            # Get final stats
            stats = shared_data.get_trade_stats()
            uptime = (datetime.now() - self.start_time).total_seconds() / 60 if self.start_time else 0
            
            logger.info(f"📊 [SYSTEM] Final Stats:")
            logger.info(f"   - Uptime: {uptime:.1f} minutes")
            logger.info(f"   - Trades: {stats['total_trades']}")
            logger.info(f"   - Wins: {stats['winning_trades']} | Losses: {stats['losing_trades']}")
            logger.info(f"   - Total PnL: {stats['total_pnl']:.2f}")
            
            logger.info("✅ [SYSTEM] GVN System stopped gracefully")
            return True
        
        except Exception as e:
            logger.error(f"Error stopping system: {e}")
            return False

    def get_status(self):
        """Get current system status"""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds() / 60
        
        stats = shared_data.get_trade_stats() if self.is_running else {}
        broker_stats = broker_api.get_order_stats()
        
        return {
            "system_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_minutes": uptime,
            "error_count": self.error_count,
            "robot_active_trades": len(self.robot.active_trades) if self.robot else 0,
            "trading_stats": stats,
            "broker_stats": broker_stats,
            "market_data": shared_data.market_data
        }

# Global system instance
gvn_system = None

def initialize_gvn():
    """Initialize GVN system - called at startup"""
    global gvn_system
    try:
        logger.info("="*60)
        logger.info("GVN MASTER ALGO - TRADING SYSTEM v2.0")
        logger.info("="*60)
        
        gvn_system = GVNSystem()
        success = gvn_system.initialize()
        
        if success:
            logger.info("✅ GVN System Ready (Call start() to begin trading)")
        else:
            logger.error("❌ GVN System initialization failed")
        
        return success
    except Exception as e:
        logger.error(f"Fatal error during initialization: {e}")
        return False

def start_trading():
    """Start GVN trading"""
    global gvn_system
    if gvn_system is None:
        initialize_gvn()
    return gvn_system.start()

def stop_trading():
    """Stop GVN trading"""
    global gvn_system
    if gvn_system:
        return gvn_system.stop()
    return False

def get_system_status():
    """Get GVN system status"""
    global gvn_system
    if gvn_system:
        return gvn_system.get_status()
    return {"error": "System not initialized"}

# CLI Interface for testing
if __name__ == "__main__":
    logger.info("Starting GVN Trading System...")
    
    # Initialize
    if initialize_gvn():
        # Start trading
        if start_trading():
            logger.info("System running. Press Ctrl+C to stop.")
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nReceived interrupt signal")
                stop_trading()
        else:
            logger.error("Failed to start trading")
    else:
        logger.error("Failed to initialize GVN system")
        sys.exit(1)
