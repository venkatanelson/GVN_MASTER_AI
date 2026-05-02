# GVN Algorithmic AI Engine - Shared Memory & Global State
# ---------------------------------------------------------
import threading

# Locks for thread-safe access
_data_lock = threading.Lock()

# Market Data LTP Storage
market_data = {
    "NIFTY": 0.0,
    "BANKNIFTY": 0.0,
    "FINNIFTY": 0.0
}

# Saving Memory to AI Engine (14 Strikes)
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
    "AngelOne": False,
    "connected_at": None
}

# 🧠 SAVING MEMORY: Permanent Backup for Broker Credentials
# (User requested to hardcode these so they don't get lost on updates)
PERMANENT_CREDENTIALS_BACKUP = {
    "broker_name": "AngelOne",
    "client_id": "P218754",
    "totp_key": "U7IPZ7XFZELCONOX6SHPM4C7I4",
    "password": "3061" # Broker PIN
    # Note: API Key and Secret are not hardcoded here because they were masked in the screenshot.
}

# Scanner Data
gvn_scanner_data = {}

# ──────────────────────────────────────────────────────────
# GVN SYSTEM STATE (Added for 25-Point Implementation)
# ──────────────────────────────────────────────────────────

# Greeks data from engine
greeks_data = {
    "ce_strikes": [],
    "pe_strikes": [],
    "last_update": None
}

# Current i-Levels (from 9:15 candle)
gvn_levels = {
    "i0": 0, "i1": 0, "i2": 0, "i3": 0, "i5": 0, "i6": 0, "i7": 0,
    "timestamp": None
}

# Active trades (both live and paper)
active_trades = {
    "live": [],
    "paper": []
}

# Sentiment score history
sentiment_history = []

# Paper trading stats
paper_trading_stats = {
    "balance": 500000,
    "total_trades": 0,
    "winning": 0,
    "losing": 0,
    "pnl": 0.0
}

# System status
system_status = {
    "initialized": False,
    "last_heartbeat": None,
    "errors": [],
    "warnings": []
}

# Thread-safe setter/getter utilities
def get_market_data():
    with _data_lock:
        return market_data.copy()

def update_market_data(key, value):
    with _data_lock:
        market_data[key] = value

def get_system_status():
    with _data_lock:
        return system_status.copy()

def add_system_error(error_msg):
    with _data_lock:
        system_status["errors"].append(error_msg)
