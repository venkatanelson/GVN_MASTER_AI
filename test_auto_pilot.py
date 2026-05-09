
import time
import json
import logging
import shared_data
from gvn_ai_delta60_engine import GVNAiDelta60Engine
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_Test_AutoPilot")

def run_dry_test():
    logger.info("🧪 [TEST] Starting GVN Auto-Pilot Dry Run...")
    
    # 1. Initialize Engine (without real Telegram for test if needed, but we want to see it)
    # Using real config if available in shared_data
    token = "7239103859:AAHTR_HkG92H3C8_p8E6v2oF_S3M-F5N2_k" # Example or from backup
    chat_id = "-1002242038525" # Example or from backup
    
    # Try to get from backup
    backup = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("telegram", {})
    if backup.get("bot_token"):
        token = backup["bot_token"]
        chat_id = backup["chat_id"]

    engine = GVNAiDelta60Engine(bot_token=token, chat_id=chat_id)
    
    # 2. Inject Mock Market Data
    symbol = "NIFTY"
    mock_spot = 24150.0
    shared_data.market_data[symbol] = mock_spot
    shared_data.market_pulse["score"] = 75 # Bullish
    shared_data.market_pulse["algo_status"] = "ON"
    shared_data.market_pulse["admin_kill_switch"] = False
    
    logger.info(f"💉 [TEST] Injected Mock Spot: {mock_spot}, Score: 75")

    # 3. Create a Mock Option Record that should trigger an entry
    # Level 7 for a strike with High: 100, Low: 80 -> result=10, n1=110, n2=90, gvn0=21.2, gvn100=172.9...
    # Let's just mock the levels calculation or the strike data
    mock_strike = {
        "strike": 24100,
        "type": "CE",
        "ltp": 95.0, # Level 7 reaction zone
        "delta": 0.60,
        "high_915": 110,
        "low_915": 90
    }
    
    # Mock records for the engine's loop
    mock_records = {
        "underlyingValue": mock_spot,
        "data": [
            {
                "strikePrice": 24100,
                "CE": {"lastPrice": 95.0, "delta": 0.60, "high_915": 110, "low_915": 90}
            }
        ],
        "filtered": {
            "CE": {"totOI": 1000000},
            "PE": {"totOI": 1500000}
        }
    }

    # 4. Trigger one cycle of the engine logic manually
    logger.info("⚡ [TEST] Triggering Trade Cycle Management...")
    engine._sync_sentiment(mock_records)
    engine._manage_trade_cycle(symbol, mock_strike)
    
    # 5. Save snapshot to Data Bank
    logger.info("📸 [TEST] Testing Data Bank Save...")
    engine._save_market_snapshot(symbol, [mock_strike])
    
    logger.info("✅ [TEST] Dry Run sequence completed. Check your Telegram for the BUY alert!")

if __name__ == "__main__":
    run_dry_test()
