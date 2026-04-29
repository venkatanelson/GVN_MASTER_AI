# shared_data.py - Master Memory for GVN Algo

# Live Market Data
market_data = {
    "NIFTY": 0.0,
    "BANKNIFTY": 0.0,
    "FINNIFTY": 0.0
}

# GVN Alpha Grid - Holds 14 strikes with levels
gvn_alpha_grid = []

# Pulse Data
market_pulse = {
    "trend": "SIDEWAYS",
    "strength": "NORMAL",
    "inst_activity": "QUIET",
    "zone": "DULL ZONE",
    "vol_ratio": 1.0
}

# Scanner Data
gvn_scanner_data = {
    "NIFTY": [],
    "BANKNIFTY": []
}

# Broker Connection Status
broker_connected = False
