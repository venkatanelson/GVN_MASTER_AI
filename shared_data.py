# GVN Algorithmic AI Engine - Shared Memory
# ---------------------------------------------------------

# Market Data LTP Storage
market_data = {
    "NIFTY": 0.0,
    "BANKNIFTY": 0.0,
    "FINNIFTY": 0.0
}

# Alpha Grid Storage (14 Strikes)
gvn_alpha_grid = []

# AI Sentiment / Market Pulse
market_pulse = {
    "mode": "INITIALIZING",
    "flow": "WAITING",
    "inst": "SCANNERS READY",
    "zone": "CHECKING TIME",
    "priority": "P1: i5 | P2: i7"
}

# Broker Connectivity Status
broker_connection_status = {
    "Shoonya": False,
    "Dhan": False,
    "connected_at": None
}

# Scanner Data
gvn_scanner_data = {}
