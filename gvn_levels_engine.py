"""
GVN i-Levels Engine: Fibonacci-based Entry/Exit Levels with Trade Setup Generation
Integrates GVN i0-i7 levels with automatic entry/target/SL calculation and expiry logic
"""

import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVNLevelsEngine")


# ───────────────────────────────────────────────────────────────
# LEGACY SUPPORT + ENHANCED CALCULATION
# ───────────────────────────────────────────────────────────────

def calculate_gvn_levels(high_915, low_915, close_915=None):
    """
    Calculates GVN Master Levels (i0-i7) based on the 9:15 AM candle.
    Enhanced with complete Fibonacci levels and trade setup info.
    """
    if not high_915 or not low_915:
        return None
        
    diff = high_915 - low_915
    result = diff / 2
    
    n1 = high_915 + result
    n2 = low_915 + result
    c1 = (n1 + n2) / 2
    
    # GVN Constants from Pine Script
    gvn0_calc = n2 * 0.118 / 0.5
    gvn_i1_calc = n1 * 0.786 / 0.5
    
    spread = gvn_i1_calc - gvn0_calc
    
    # Calculate all levels with Fibonacci ratios
    levels = {
        "timestamp": datetime.now().isoformat(),
        "high_915": round(high_915, 2),
        "low_915": round(low_915, 2),
        "close_915": round(close_915, 2) if close_915 else None,
        "n1": round(n1, 2),
        "n2": round(n2, 2),
        "c1": round(c1, 2),
        "range": round(diff, 2),
        "i0": round(gvn_i1_calc, 2),
        "i1": round(gvn0_calc, 2),      # Zero-to-Hero level (priority on expiry)
        "i2": round(gvn0_calc + 0.763 * spread, 2),
        "i3": round(gvn0_calc + 0.618 * spread, 2),
        "i5": round(gvn0_calc + 0.5 * spread, 2),   # Momentum level
        "i6": round(gvn0_calc + 0.382 * spread, 2),
        "i7": round(gvn0_calc + 0.220 * spread, 2), # Entry level
        "sl": 12  # Default SL as per script
    }
    return levels


def process_alpha_grid(strike_data_list):
    """
    Processes multiple strikes (usually 14) and calculates levels for each.
    strike_data_list = [{'symbol': 'NIFTY24200CE', 'high': 151, 'low': 135, 'delta': 0.65}, ...]
    """
    grid_results = []
    for strike in strike_data_list:
        levels = calculate_gvn_levels(strike['high'], strike['low'])
        if levels:
            grid_results.append({
                "symbol": strike['symbol'],
                "delta": strike.get('delta', 0.0),
                "levels": levels,
                "current_price": strike.get('ltp', 0.0)
            })
    return grid_results


# ───────────────────────────────────────────────────────────────
# TRADE SETUP GENERATOR
# ───────────────────────────────────────────────────────────────

class TradeSetupGenerator:
    """Generate complete trade setup from GVN levels"""
    
    ENTRY_BUFFER = 1.0
    EXIT_BUFFER = 0.5
    FIXED_SL = 12
    
    STRATEGY_TARGETS = {
        "Strategy 1": {"i7": "i3", "i5": "i1"},
        "Strategy 2": {"i5": "i1", "i7": "i5"},
        "Strategy 3": {"i1": "i5", "i5": "i2"},  # Expiry day: i1 priority
    }
    
    def __init__(self, levels, strategy="Strategy 1"):
        self.levels = levels
        self.strategy = strategy
    
    def generate_trade(self, entry_level_name):
        """Generate complete trade for specific i-level"""
        if not self.levels or entry_level_name not in self.levels:
            return None
        
        entry_price = self.levels[entry_level_name]
        buffered_entry = entry_price + self.ENTRY_BUFFER
        sl_price = entry_price - self.FIXED_SL
        buffered_sl = sl_price - self.EXIT_BUFFER
        
        # Get target from strategy
        target_name = self.STRATEGY_TARGETS.get(self.strategy, {}).get(entry_level_name, "i1")
        target_price = self.levels.get(target_name, entry_price + 10)
        buffered_target = target_price + self.EXIT_BUFFER
        
        return {
            "entry_level": entry_level_name,
            "entry_price": round(entry_price, 2),
            "buffered_entry": round(buffered_entry, 2),
            "sl_price": round(sl_price, 2),
            "buffered_sl": round(buffered_sl, 2),
            "target_level": target_name,
            "target_price": round(target_price, 2),
            "buffered_target": round(buffered_target, 2),
            "risk_points": round(entry_price - sl_price, 2),
            "reward_points": round(buffered_target - buffered_entry, 2),
            "risk_reward_ratio": round((buffered_target - buffered_entry) / (entry_price - sl_price), 2) if (entry_price - sl_price) > 0 else 0,
            "status": "READY"
        }
    
    def get_all_trades(self):
        """Generate all priority trades"""
        trades = []
        for level in ["i5", "i7", "i3", "i1"]:  # Priority order
            if level in self.levels:
                trade = self.generate_trade(level)
                if trade and trade["risk_reward_ratio"] >= 1.5:  # Minimum 1.5:1
                    trades.append(trade)
        return trades


# ───────────────────────────────────────────────────────────────
# EXPIRY & SQUARE-OFF LOGIC
# ───────────────────────────────────────────────────────────────

def is_expiry_day():
    """Check if today is Thursday (weekly expiry)"""
    return datetime.now().weekday() == 3

def is_square_off_time():
    """Check if past 3:15 PM"""
    now = datetime.now()
    return now.hour >= 15 and now.minute >= 15

def get_expiry_strategy():
    """Return i1 (Zero-to-Hero) priority on expiry"""
    if is_expiry_day():
        logger.info("🎯 EXPIRY: Shifting to i1 priority for gamma burst")
        return "Strategy 3"
    return "Strategy 1"
