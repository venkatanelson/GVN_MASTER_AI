import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import traceback
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import shared_data
import nse_option_chain

# Let's import app and db to see if they fail
try:
    from app import app, db, User, UserBrokerConfig, AlgoTrade
    print("✓ Successfully imported app, db, User, UserBrokerConfig, AlgoTrade")
except Exception as e:
    print(f"❌ Failed to import app: {e}")
    traceback.print_exc()
    sys.exit(1)

# Let's mock a user and config in database session or mock the query
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

# Set active symbol
shared_data.active_dashboard_symbol = "NIFTY"

# Let's call execute_live_trade_for_active_users directly with mocks
with patch('app.User') as mock_User:
    with patch('app.UserBrokerConfig') as mock_UserBrokerConfig:
        with patch('app.AlgoTrade') as mock_AlgoTrade:
            mock_User.query.filter_by.return_value.all.return_value = [mock_user]
            mock_UserBrokerConfig.query.filter_by.return_value.first.return_value = mock_config
            mock_AlgoTrade.query.filter_by.return_value.order_by.return_value.first.return_value = None
            
            try:
                print("Running execute_live_trade_for_active_users...")
                nse_option_chain.execute_live_trade_for_active_users("NIFTY_23550_CE", "BUY", 180.2, "Test")
                print("Execution complete without critical error.")
            except Exception as ex:
                print(f"Caught critical error: {ex}")
                traceback.print_exc()
