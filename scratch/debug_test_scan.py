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

# Inspect what nse_option_chain does internally:
print("--- STARTING TRACE ---")
symbol = "NIFTY"
records = mock_records["records"]
underlying_value = 23550.0
atm = 23550.0
step = 50

# Replicate forced_strikes generation
ce_strikes = [23350, 23400, 23450, 23500, 23550, 23600, 23650]
pe_strikes = [23450, 23500, 23550, 23600, 23650, 23700, 23750]
forced_strikes = []
for s in ce_strikes:
    forced_strikes.append(f"{s} CE")
for s in pe_strikes:
    forced_strikes.append(f"{s} PE")
forced_strikes = list(set(forced_strikes))

print(f"forced_strikes = {forced_strikes}")

all_options = []
for item in records.get("data", []):
    if "CE" in item:
        item["CE"]["type"] = "CE"
        all_options.append(item["CE"])
    if "PE" in item:
        item["PE"]["type"] = "PE"
        all_options.append(item["PE"])
    if "type" in item:
        all_options.append(item)

print(f"all_options count = {len(all_options)}")
print(f"all_options[0] = {all_options[0] if all_options else 'None'}")

# Run dynamic selection logic trace
for strike_name in forced_strikes:
    s_price = int(strike_name.split()[0])
    s_type = strike_name.split()[1].upper()
    
    # Let's see if it finds match in all_options
    strike_data = None
    for opt in all_options:
        opt_strike = opt.get("strikePrice") or opt.get("strike")
        opt_type = str(opt.get("type", "")).upper() or str(opt.get("optionType", "")).upper()
        
        if opt_strike == s_price and s_type in opt_type:
            strike_data = opt
            break
            
    if strike_name == "23550 CE":
        print(f"For 23550 CE: strike_data found? {strike_data is not None}")
        if strike_data:
            print(f"strike_data = {strike_data}")
            
    if not strike_data or float(strike_data.get("lastPrice") or 0) == 0:
        # Trace emulated fallback
        spot = records.get("underlyingValue", 0)
        if spot > 0:
            if s_type == "CE":
                offset = 192.80 if s_price == 23650 else 150.0
                emulated_lp = max(spot - s_price, 0) + offset
            else:
                offset = 161.40 if s_price == 23750 else 150.0
                emulated_lp = max(s_price - spot, 0) + offset
            emulated_lp = round(emulated_lp, 2)
            strike_data = {
                "strikePrice": s_price, "strike": s_price, "type": s_type,
                "lastPrice": emulated_lp, "changeinOpenInterest": 0, "totalTradedVolume": 0
            }
            if strike_name == "23550 CE":
                print(f"Emulated fallback for 23550 CE: {strike_data}")

    lp = float(strike_data.get("lastPrice") or strike_data.get("ltp") or 0)
    if strike_name == "23550 CE":
        print(f"LTP for 23550 CE = {lp}")

    ohlc_915 = (220.0, 180.0) # mocked get_real_option_915_ohlc
    calc_levels = mock_calculate_gvn_levels(ohlc_915[0], ohlc_915[1])
    custom_levels = {
        "i1": calc_levels["i1"], "i2": calc_levels["i2"], "i3": calc_levels["i3"], 
        "i5": calc_levels["i5"], "i6": calc_levels["i6"], "i7": calc_levels["i7"], "i0": calc_levels["i0"],
        "sl": round(calc_levels["i6"] - 12.0, 2)
    }
    
    # append scanner
    if symbol not in nse_option_chain.gvn_scanner_data:
        nse_option_chain.gvn_scanner_data[symbol] = []
        
    if not any(x['strike'] == strike_name for x in nse_option_chain.gvn_scanner_data[symbol]):
        nse_option_chain.gvn_scanner_data[symbol].append({
            "strike": strike_name,
            "ltp": lp,
            "delta": 0.65,
            "oi_change": strike_data.get('changeinOpenInterest') or 0,
            "volume": strike_data.get('totalTradedVolume') or 0,
            "score": 95, 
            "zone": "🚀 AUTHORIZED TRACK",
            "pressure": "🟢 LEVEL READY",
            "ai_signal": "i-LADDER",
            "i_level": "MANUAL",
            "potential": "HIGH",
            "levels": custom_levels
        })

print(f"Total scanner data populated in nse_option_chain.gvn_scanner_data: {len(nse_option_chain.gvn_scanner_data.get(symbol, []))}")
