import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shared_data
import nse_option_chain
import broker_api

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

# Save original exists to prevent breaking other libraries like dotenv
original_exists = os.path.exists

def mock_exists(path):
    if "morning_locked_strikes.json" in str(path):
        return False
    return original_exists(path)

class TestGVNAlgoSystem(unittest.TestCase):
    def setUp(self):
        # Clear/reset states
        shared_data.fast_polling_mode = False
        shared_data.last_touched_levels = {}
        shared_data.last_pre_alerts = {}
        shared_data.demo_trade = {"active": False, "symbol": None, "entry_price": 0, "target": 0, "sl": 0, "qty": 50}
        shared_data.market_data = {"NIFTY": 23550.0}
        shared_data.gvn_scanner_data = {}
        shared_data.gvn_915_benchmark = {
            "NIFTY": {"high": 23600.0, "low": 23500.0, "captured": True, "date": "2026-05-22"}
        }

    @patch('nse_option_chain.calculate_gvn_levels', side_effect=mock_calculate_gvn_levels)
    @patch('nse_option_chain.get_angel_token', return_value='mock_token')
    @patch('nse_option_chain.get_real_option_915_ohlc', return_value=(220.0, 180.0))
    @patch('broker_api.get_angel_option_ltps')
    @patch('broker_api.place_order_universal')
    @patch('gvn_telegram_engine.TelegramAlertManager')
    @patch('os.path.exists', side_effect=mock_exists)
    def test_pre_alert_and_polling_speed(self, mock_exists_func, mock_tg, mock_place, mock_ltps, mock_ohlc, mock_token, mock_calc):
        # Setup mock records for NIFTY option chain
        # LTP is 182.0, close to i6 (180.0) and i5 (185.0) -> distance is 2.0 and 3.0 (1.5 <= dist <= 7.0)
        with patch('nse_option_chain.find_angel_token_and_segment', return_value=('12345', 'NFO')):
            mock_ltps.return_value = {'12345': 182.0}
            
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
                                "lastPrice": 182.0,
                                "changeinOpenInterest": 1000,
                                "totalTradedVolume": 5000,
                                "openInterest": 20000,
                                "delta": 0.60
                            }
                        }
                    ]
                }
            }
            
            # Set wind direction to be aligned
            nse_option_chain.market_pulse["NIFTY"] = {"wind_direction": "UP WIND", "sentiment": "NEUTRAL"}
            
            # Run scanner
            nse_option_chain.analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_records)
            
            # Verify fast polling is activated
            print(f"DEBUG: fast_polling_mode = {shared_data.fast_polling_mode}")
            self.assertTrue(shared_data.fast_polling_mode)
            
            # Verify pre-alerts triggered (last_pre_alerts has keys for i6 and i5)
            print(f"DEBUG: last_pre_alerts = {shared_data.last_pre_alerts}")
            self.assertEqual(len(shared_data.last_pre_alerts), 2)
            
            # Verify no order is placed yet
            mock_place.assert_not_called()

    @patch('nse_option_chain.calculate_gvn_levels', side_effect=mock_calculate_gvn_levels)
    @patch('nse_option_chain.get_angel_token', return_value='mock_token')
    @patch('nse_option_chain.get_real_option_915_ohlc', return_value=(220.0, 180.0))
    @patch('broker_api.get_angel_option_ltps')
    @patch('broker_api.place_order_universal', return_value='ORDER123')
    @patch('gvn_telegram_engine.TelegramAlertManager')
    @patch('app.User')
    @patch('app.UserBrokerConfig')
    @patch('app.AlgoTrade')
    @patch('app.db')
    @patch('os.path.exists', side_effect=mock_exists)
    def test_level_touch_entry_order(self, mock_exists_func, mock_db, mock_AlgoTrade, mock_UserBrokerConfig, mock_User, mock_tg, mock_place, mock_ltps, mock_ohlc, mock_token, mock_calc):
        # Mock database queries for active users
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = 'Venkat'
        mock_user.trade_lots = 1
        mock_user.user_type = 'LIVE'
        mock_user.is_approved = True
        mock_user.expiry_date = datetime.utcnow() + timedelta(days=30)
        mock_user.algo_status = 'ON'
        mock_user.is_blocked = False
        mock_User.query.filter_by.return_value.all.return_value = [mock_user]
        
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
        mock_UserBrokerConfig.query.filter_by.return_value.first.return_value = mock_config
        
        mock_AlgoTrade.query.filter_by.return_value.order_by.return_value.first.return_value = None

        # LTP is 180.5, close to i6 (180.0) -> distance is 0.5 (< 1.5) -> Touch Entry
        with patch('nse_option_chain.find_angel_token_and_segment', return_value=('12345', 'NFO')):
            mock_ltps.return_value = {'12345': 180.5}
            
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
                                "lastPrice": 180.5,
                                "changeinOpenInterest": 1000,
                                "totalTradedVolume": 5000,
                                "openInterest": 20000,
                                "delta": 0.60
                            }
                        }
                    ]
                }
            }
            
            # Set wind direction to be aligned
            nse_option_chain.market_pulse["NIFTY"] = {"wind_direction": "UP WIND", "sentiment": "NEUTRAL"}
            
            # Run scanner
            nse_option_chain.analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_records)
            
            # Verify level touched alert stored
            print(f"DEBUG: last_touched_levels = {shared_data.last_touched_levels}")
            self.assertEqual(len(shared_data.last_touched_levels), 1)
            
            # Wait brief moment for async thread order routing to execute
            time.sleep(0.3)
            
            # Verify order placed
            self.assertTrue(mock_place.called)
            print(f"DEBUG: place_order_universal called with: {mock_place.call_args_list}")

    @patch('nse_option_chain.calculate_gvn_levels', side_effect=mock_calculate_gvn_levels)
    @patch('nse_option_chain.get_angel_token', return_value='mock_token')
    @patch('nse_option_chain.get_real_option_915_ohlc', return_value=(220.0, 180.0))
    @patch('broker_api.get_angel_option_ltps')
    @patch('broker_api.place_order_universal', return_value='ORDER123')
    @patch('gvn_telegram_engine.TelegramAlertManager')
    @patch('app.User')
    @patch('app.UserBrokerConfig')
    @patch('app.AlgoTrade')
    @patch('app.db')
    @patch('os.path.exists', side_effect=mock_exists)
    def test_target_and_sl_exits(self, mock_exists_func, mock_db, mock_AlgoTrade, mock_UserBrokerConfig, mock_User, mock_tg, mock_place, mock_ltps, mock_ohlc, mock_token, mock_calc):
        # Mock database queries for active users
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = 'Venkat'
        mock_user.trade_lots = 1
        mock_user.user_type = 'LIVE'
        mock_user.is_approved = True
        mock_user.expiry_date = datetime.utcnow() + timedelta(days=30)
        mock_user.algo_status = 'ON'
        mock_user.is_blocked = False
        mock_User.query.filter_by.return_value.all.return_value = [mock_user]
        
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
        mock_UserBrokerConfig.query.filter_by.return_value.first.return_value = mock_config
        
        # Mock an open trade for target hit
        mock_open_trade = MagicMock()
        mock_open_trade.id = 101
        mock_open_trade.entry_price = 180.0
        mock_AlgoTrade.query.filter_by.return_value.order_by.return_value.first.return_value = mock_open_trade

        # Test Case 1: Target Hit
        # Preset active demo trade
        shared_data.demo_trade = {
            "active": True,
            "symbol": "NIFTY_23550_CE",
            "entry_price": 180.0,
            "target": 200.0,
            "sl": 168.0,
            "qty": 50
        }
        
        with patch('nse_option_chain.find_angel_token_and_segment', return_value=('12345', 'NFO')):
            # LTP goes to 205.0 (Target hit!)
            mock_ltps.return_value = {'12345': 205.0}
            
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
                                "lastPrice": 205.0,
                                "changeinOpenInterest": 1000,
                                "totalTradedVolume": 5000,
                                "openInterest": 20000,
                                "delta": 0.60
                            }
                        }
                    ]
                }
            }
            
            nse_option_chain.market_pulse["NIFTY"] = {"wind_direction": "UP WIND", "sentiment": "NEUTRAL"}
            
            # Run scanner
            nse_option_chain.analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_records)
            
            # Verify demo trade is deactivated
            self.assertFalse(shared_data.demo_trade["active"])
            
            # Wait for async thread order routing to execute
            time.sleep(0.3)
            
            # Verify SELL order was placed
            self.assertTrue(mock_place.called)
            # Find the sell call
            sell_call = False
            for call in mock_place.call_args_list:
                args = call[0]
                if args[2] == 'SELL':
                    sell_call = True
                    break
            self.assertTrue(sell_call, "SELL order was not triggered for target exit")
            
        # Reset mocks and test Stop Loss Hit
        mock_place.reset_mock()
        
        # Preset active demo trade again
        shared_data.demo_trade = {
            "active": True,
            "symbol": "NIFTY_23550_CE",
            "entry_price": 180.0,
            "target": 200.0,
            "sl": 168.0,
            "qty": 50
        }
        
        with patch('nse_option_chain.find_angel_token_and_segment', return_value=('12345', 'NFO')):
            # LTP falls to 165.0 (Stop loss hit!)
            mock_ltps.return_value = {'12345': 165.0}
            
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
                                "lastPrice": 165.0,
                                "changeinOpenInterest": 1000,
                                "totalTradedVolume": 5000,
                                "openInterest": 20000,
                                "delta": 0.60
                            }
                        }
                    ]
                }
            }
            
            # Run scanner
            nse_option_chain.analyze_and_update_gvn_scanner("NIFTY", mock_external_data=mock_records)
            
            # Verify demo trade is deactivated
            self.assertFalse(shared_data.demo_trade["active"])
            
            # Wait for async thread order routing to execute
            time.sleep(0.3)
            
            # Verify SELL order was placed
            self.assertTrue(mock_place.called)
            sell_call = False
            for call in mock_place.call_args_list:
                args = call[0]
                if args[2] == 'SELL':
                    sell_call = True
                    break
            self.assertTrue(sell_call, "SELL order was not triggered for SL exit")

if __name__ == '__main__':
    unittest.main()
