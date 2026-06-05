# GVN Zero-to-Hero Strategy Test Script
import os
import sys
import logging
from datetime import datetime

# Setup paths and logger
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestZ2H")

import shared_data
import nse_option_chain
from nse_option_chain import analyze_and_update_gvn_scanner, calculate_gvn_levels

# Monkey-patch get_real_option_915_ohlc for deterministic simulation
strike_high = 180.0
strike_low = 90.0
nse_option_chain.get_real_option_915_ohlc = lambda symbol, strike, opt_type, expiry_str=None: (strike_high, strike_low)

# Monkey-patch wind_engine.get_market_dna to return UP WIND
def mock_get_market_dna(*args, **kwargs):
    return {
        "wind_engine": {
            "wind_state": "UP WIND",
            "wind_power": "STRONG",
            "trend_type": "SAFE"
        },
        "smart_money_status": "BULLISH"
    }
nse_option_chain.wind_engine.get_market_dna = mock_get_market_dna

# Monkey-patch gvn_data_bank to bypass actual db write
import gvn_data_bank
gvn_data_bank.save_option_915_benchmark = lambda *a, **kw: None

def run_z2h_test():
    logger.info("🎬 Starting Zero-to-Hero Expiry Strategy Simulation...")
    
    # 1. Initialize global states
    shared_data.gvn_z2h_watchlist = []
    
    # Set initial wind direction
    nse_option_chain.market_pulse["NIFTY"] = {
        "wind_direction": "UP WIND",
        "sentiment": "BULLISH",
        "score": 75,
        "trend": "BULLISH"
    }
    
    levels = calculate_gvn_levels(strike_high, strike_low)
    target1 = levels["i7"]
    bottom_level = levels["i0"]
    
    # 2. Run scan 1: Option LTP is 140 (Above bottom level, status should be PENDING ENTRY)
    mock_data_1 = {
        "timestamp": "2026-06-04 09:30:00",
        "records": {
            "underlyingValue": 23250.0,
            "expiryDates": ["04-Jun-2026"],
            "data": [
                {
                    "strikePrice": 23250,
                    "CE": {
                        "strikePrice": 23250,
                        "lastPrice": 140.0,
                        "changeinOpenInterest": 50000,
                        "totalTradedVolume": 200000,
                        "openInterest": 1500000,
                        "delta": 0.52,
                        "high_915": strike_high,
                        "low_915": strike_low
                    }
                }
            ]
        },
        "source": "MOCK_PLAYBACK"
    }
    
    logger.info("--------------------------------------------------")
    logger.info("STEP 1: Checking Candidate Addition (LTP = 140)")
    logger.info("--------------------------------------------------")
    analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_data_1)
    
    watchlist = getattr(shared_data, 'gvn_z2h_watchlist', [])
    if len(watchlist) == 0:
        logger.error("❌ Test Failed: Watchlist is empty, candidate not added!")
        return False
    
    item = watchlist[0]
    logger.info(f"✓ Watchlist item added: {item['strike_name']}")
    logger.info(f"  - Status: {item['status']}")
    
    if item['status'] != "PENDING ENTRY":
        logger.error(f"❌ Test Failed: Expected PENDING ENTRY, got {item['status']}")
        return False
        
    # 3. Run scan 2: Option LTP drops to bottom_level (within ±3 points), Wind is UP WIND -> status becomes ACTIVE
    mock_data_2 = {
        "timestamp": "2026-06-04 09:35:00",
        "records": {
            "underlyingValue": 23250.0,
            "expiryDates": ["04-Jun-2026"],
            "data": [
                {
                    "strikePrice": 23250,
                    "CE": {
                        "strikePrice": 23250,
                        "lastPrice": bottom_level,
                        "changeinOpenInterest": 50000,
                        "totalTradedVolume": 200000,
                        "openInterest": 1500000,
                        "delta": 0.52,
                        "high_915": strike_high,
                        "low_915": strike_low
                    }
                }
            ]
        },
        "source": "MOCK_PLAYBACK"
    }
    
    logger.info("--------------------------------------------------")
    logger.info(f"STEP 2: Checking Entry Trigger (LTP = {bottom_level})")
    logger.info("--------------------------------------------------")
    analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_data_2)
    
    item = shared_data.gvn_z2h_watchlist[0]
    logger.info(f"  - Status after bottom touch: {item['status']}")
    logger.info(f"  - Entry Price: {item['entry_price']}")
    logger.info(f"  - Stop Loss: {item['sl']}")
    
    if item['status'] != "ACTIVE":
        logger.error(f"❌ Test Failed: Expected ACTIVE, got {item['status']}")
        return False

    # 4. Run scan 3: Option LTP goes up to Target 1 -> status becomes T1 HIT
    mock_data_3 = {
        "timestamp": "2026-06-04 09:40:00",
        "records": {
            "underlyingValue": 23250.0,
            "expiryDates": ["04-Jun-2026"],
            "data": [
                {
                    "strikePrice": 23250,
                    "CE": {
                        "strikePrice": 23250,
                        "lastPrice": target1,
                        "changeinOpenInterest": 50000,
                        "totalTradedVolume": 200000,
                        "openInterest": 1500000,
                        "delta": 0.52,
                        "high_915": strike_high,
                        "low_915": strike_low
                    }
                }
            ]
        },
        "source": "MOCK_PLAYBACK"
    }
    
    logger.info("--------------------------------------------------")
    logger.info(f"STEP 3: Checking Target 1 Hit (LTP = {target1})")
    logger.info("--------------------------------------------------")
    analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_data_3)
    
    item = shared_data.gvn_z2h_watchlist[0]
    logger.info(f"  - Status after target 1 hit: {item['status']}")
    
    if item['status'] != "T1 HIT":
        logger.error(f"❌ Test Failed: Expected T1 HIT, got {item['status']}")
        return False

    # 5. Run scan 4: Option LTP drops to stop loss -> status becomes SL HIT
    sl_price = item['sl']
    mock_data_4 = {
        "timestamp": "2026-06-04 09:45:00",
        "records": {
            "underlyingValue": 23250.0,
            "expiryDates": ["04-Jun-2026"],
            "data": [
                {
                    "strikePrice": 23250,
                    "CE": {
                        "strikePrice": 23250,
                        "lastPrice": sl_price,
                        "changeinOpenInterest": 50000,
                        "totalTradedVolume": 200000,
                        "openInterest": 1500000,
                        "delta": 0.52,
                        "high_915": strike_high,
                        "low_915": strike_low
                    }
                }
            ]
        },
        "source": "MOCK_PLAYBACK"
    }
    
    logger.info("--------------------------------------------------")
    logger.info(f"STEP 4: Checking SL Exit Trigger (LTP = {sl_price})")
    logger.info("--------------------------------------------------")
    analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_data_4)
    
    item = shared_data.gvn_z2h_watchlist[0]
    logger.info(f"  - Status after SL hit: {item['status']}")
    
    if item['status'] != "SL HIT":
        logger.error(f"❌ Test Failed: Expected SL HIT, got {item['status']}")
        return False
        
    logger.info("✅ SUCCESS: All Zero-to-Hero simulation stages passed perfectly!")
    return True

if __name__ == "__main__":
    success = run_z2h_test()
    sys.exit(0 if success else 1)
