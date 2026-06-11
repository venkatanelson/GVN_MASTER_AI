import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import shared_data
import nse_option_chain

# Setup states identical to the test
shared_data.fast_polling_mode = False
shared_data.last_touched_levels = {}
shared_data.last_pre_alerts = {}
shared_data.demo_trade = {"active": False, "symbol": None, "entry_price": 0, "target": 0, "sl": 0, "qty": 50}
shared_data.market_data = {"NIFTY": 23550.0}
shared_data.gvn_scanner_data = {}
shared_data.gvn_915_benchmark = {
    "NIFTY": {"high": 23600.0, "low": 23500.0, "captured": True, "date": "2026-05-22"}
}
shared_data.active_dashboard_symbol = "NIFTY"

def mock_calculate_gvn_levels(high, low):
    return {
        "i1": 210.0,
        "i0": 150.0,
        "i2": 195.0,
        "i3": 190.0,
        "i5": 185.0,
        "i6": 180.0,
        "i7": 160.0
    }

mock_dna_bullish = {
    "wind_engine": {
        "wind_state": "UP WIND",
        "wind_power": "STRONG",
        "trend_type": "BULLISH"
    },
    "smart_money_status": "BULLS DOMINATING"
}

# Mock database
mock_user = MagicMock()
mock_user.id = 1
mock_user.username = 'Venkat'
mock_user.trade_lots = 1
mock_user.user_type = 'LIVE'
mock_user.is_approved = True
mock_user.expiry_date = datetime.utcnow() + timedelta(days=30)
mock_user.algo_status = 'ON'
mock_user.is_blocked = False

mock_config = MagicMock()
mock_config.broker_name = 'angel'
mock_config.client_id = 'V12345'
mock_config.get_credentials.return_value = {
    'password': 'p',
    'api_key': 'k',
    'api_secret': 's',
    'totp_key': 't'
}
mock_config.webhook_url = 'http://example.com'
mock_config.tv_secret = 'secret'

mock_records = {
    "records": {
        "underlyingValue": 23550.0,
        "expiryDates": ["28-May-2026"],
        "data": [
            {
                "strikePrice": 23550,
                "CE": {
                    "strikePrice": 23550,
                    "type": "CE",
                    "lastPrice": 180.2,
                    "changeinOpenInterest": 1000,
                    "totalTradedVolume": 5000,
                    "openInterest": 20000,
                    "delta": 0.60
                }
            }
        ]
    }
}

# Mock exists to return False
def mock_exists(path):
    if "morning_locked_strikes.json" in str(path):
        return False
    return os.path.exists(path)

# Run actual scan with print statements in nse_option_chain active
with patch('nse_option_chain.calculate_gvn_levels', side_effect=mock_calculate_gvn_levels):
    with patch('nse_option_chain.get_angel_token', return_value='mock_token'):
        with patch('nse_option_chain.get_real_option_915_ohlc', return_value=(220.0, 180.0)):
            with patch('broker_api.get_angel_option_ltps') as mock_ltps:
                with patch('broker_api.place_order_universal', return_value='ORDER123') as mock_place:
                    with patch('app.User') as mock_User:
                        with patch('app.UserBrokerConfig') as mock_UserBrokerConfig:
                            with patch('app.AlgoTrade') as mock_AlgoTrade:
                                with patch('os.path.exists', side_effect=mock_exists):
                                    mock_User.query.filter_by.return_value.all.return_value = [mock_user]
                                    mock_UserBrokerConfig.query.filter_by.return_value.first.return_value = mock_config
                                    mock_AlgoTrade.query.filter_by.return_value.order_by.return_value.first.return_value = None
                                    mock_AlgoTrade.__name__ = 'AlgoTrade'
                                    
                                    nse_option_chain.market_pulse["NIFTY"] = {"wind_direction": "UP WIND", "sentiment": "NEUTRAL"}
                                    mock_ltps.return_value = {'12345': 180.2}
                                    
                                    with patch('nse_option_chain.find_angel_token_and_segment', return_value=('12345', 'NFO')):
                                        with patch('gvn_ai_wind_engine.GVNAiWindEngine.get_market_dna', return_value=mock_dna_bullish):
                                            # Run scanner
                                            print("--- RUNNING ACTUAL SCANNER WITH EXISTS MOCKED ---")
                                            nse_option_chain.analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_records)
                                            print(f"DEBUG: place_order_universal called? {mock_place.called}")
