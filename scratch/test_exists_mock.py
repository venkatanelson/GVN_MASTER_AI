import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import nse_option_chain
from unittest.mock import patch

def mock_exists(path):
    if "morning_locked_strikes.json" in str(path):
        return False
    return os.path.exists(path)

@patch('os.path.exists', side_effect=mock_exists)
def test_func(mock_exists_obj):
    import os
    print(f"Inside test: os.path.exists('morning_locked_strikes.json') = {os.path.exists('morning_locked_strikes.json')}")
    import nse_option_chain
    print(f"Inside test (via module): os.path.exists = {nse_option_chain.os.path.exists('morning_locked_strikes.json')}")

print(f"Before patch: os.path.exists('morning_locked_strikes.json') = {os.path.exists('morning_locked_strikes.json')}")
test_func()
print(f"After patch: os.path.exists('morning_locked_strikes.json') = {os.path.exists('morning_locked_strikes.json')}")
