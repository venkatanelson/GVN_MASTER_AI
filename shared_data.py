# GVN Algorithmic AI Engine - Shared Memory & Global State
# ---------------------------------------------------------
import threading

# Locks for thread-safe access
_data_lock = threading.Lock()

# Market Data LTP Storage
market_data = {
    "NIFTY": 24119.30,
    "BANKNIFTY": 54878.50,
    "FINNIFTY": 21400.10,
    "CRUDEOIL": 6842.00
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
PERMANENT_CREDENTIALS_BACKUP = {
    "angel": {
        "broker_name": "AngelOne",
        "client_id": "P218754",
        "totp_key": "U7IPZ7XFZELCONOX6SHPM4C7I4",
        "password": "3061", # Broker PIN
        "api_key": "vS42B24z",
        "api_secret": "" # Optional
    },
    "shoonya": {
        "broker_name": "Shoonya",
        "client_id": "FA440429",
        "password": "Kalavathi@12",
        "api_secret": "Hjh4nR9yXnn4xF9i4ALKrj1AaZyJ4hlllChq5HHo4qXX9HOXNhdIhNCGXigRJ4d4",
        "vendor_code": "venkata",
        "totp_key": "II5QTH6E4GXE4OWEAY6Y62C5XQ2Y2B65"
    }
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
