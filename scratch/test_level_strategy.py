import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shared_data
from gvn_ai_delta60_engine import GVNAiDelta60Engine

def test_level_to_level_strategy():
    print("[TEST] Running test_level_to_level_strategy...")
    
    # Initialize Engine
    engine = GVNAiDelta60Engine()
    engine.telegram = MagicMock() # Mock Telegram
    engine.paper_trading = MagicMock() # Mock Paper Trading
    engine.paper_trading.execute_paper_buy.return_value = {"id": "vtrade_123"}
    
    # Define mock GVN levels
    # Let's say levels are:
    # i1=57, i7=149, i6=216, i5=266, i3=315, i2=375, i0=400
    mock_levels = {
        "i1": 57.0,
        "i7": 149.0,
        "i6": 216.0,
        "i5": 266.0,
        "i3": 315.0,
        "i2": 375.0,
        "i0": 400.0
    }
    
    # Setup mock strike and market state
    strike = {
        "strike": 23550,
        "type": "CE",
        "ltp": 56.0,
        "high_915": 100.0,
        "low_915": 50.0,
        "symbol": "NIFTY23550CE",
        "delta": 0.60
    }
    
    # Setup market pulse
    shared_data.market_pulse["score"] = 70
    shared_data.market_pulse["wind_direction"] = "UP WIND"
    shared_data.market_pulse["wind_power"] = 1.0
    shared_data.market_pulse["nifty50_trend_signal"] = "STRONG BULLISH"
    
    # Conditionally mock os.path.exists for morning_locked_strikes.json
    orig_exists = os.path.exists
    def side_effect(path):
        if "morning_locked_strikes.json" in str(path):
            return False
        return orig_exists(path)
        
    with patch('os.path.exists', side_effect=side_effect):
        with patch('gvn_levels_engine.calculate_gvn_levels', return_value=mock_levels):
            
            # Test Morning Preference for normal day (monitors i5 = 266)
            # First entry: price is 56.0. Previous price is 55.0. 
            # Crossover of i1 (57.0) is triggered, but since it's normal day,
            # it requires preference level i5 (266) for the first entry.
            # Thus, first entry on i1 should be blocked.
            engine.memory["last_ltps"] = {"23550_CE": 55.0}
            strike["ltp"] = 57.1
            
            # Run trade cycle
            engine._manage_trade_cycle("NIFTY", strike)
            
            # Verify no trade was opened (active_trades should be empty)
            assert len(engine.memory["active_trades"]) == 0
            print("   ✅ SUCCESS: Non-preference level morning entry blocked successfully.")
            
            # Now test crossover of preference level i5 (266.0)
            # Previous price 265.0, current price 266.1.
            engine.memory["last_ltps"]["23550_CE"] = 265.0
            strike["ltp"] = 266.1
            
            engine._manage_trade_cycle("NIFTY", strike)
            
            # Verify trade was opened
            trade_key = "23550_CE"
            assert trade_key in engine.memory["active_trades"]
            trade = engine.memory["active_trades"][trade_key]
            print(f"   ✅ SUCCESS: Trade entered at preference level {trade['entry']:.2f}")
            print(f"      Target Level: {trade['target']:.2f} (Expected: 315.0)")
            print(f"      Stop Loss: {trade['sl']:.2f} (Expected: 254.0)")
            
            assert trade["entry"] == 266.0
            assert trade["target"] == 315.0 # next level above i5 (266) is i3 (315)
            assert trade["sl"] == 254.0 # 266 - 12
            
            # Check Telegram was called once with BUY
            assert engine.telegram.send_alert.call_count >= 1
            last_alert = engine.telegram.send_alert.call_args[0][0]
            print("      Telegram Entry Alert sent:\n", last_alert)
            assert "NEW ENTRY" in last_alert
            assert "I5" in last_alert
            assert "315.00" in last_alert
            assert "254.00" in last_alert
            
            # Reset mock calls
            engine.telegram.send_alert.reset_mock()
            
            # 2. Test Target Hit
            strike["ltp"] = 315.5
            engine._manage_trade_cycle("NIFTY", strike)
            
            # Trade should be closed and removed from active trades
            assert trade_key not in engine.memory["active_trades"]
            print("   ✅ SUCCESS: Target hit exit triggered successfully.")
            
            # Check Exit Alert
            assert engine.telegram.send_alert.call_count >= 1
            exit_alert = engine.telegram.send_alert.call_args[0][0]
            print("      Telegram Exit Alert sent:\n", exit_alert)
            assert "POSITION CLOSED" in exit_alert
            assert "Target Hit" in exit_alert
            assert "315.5" in exit_alert

if __name__ == "__main__":
    test_level_to_level_strategy()
