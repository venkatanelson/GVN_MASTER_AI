import shared_data
import gvn_alpha_engine
import gvn_levels_engine
import nse_option_chain
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeltaLevelsEngine")

# Global cache for high-priority strikes
priority_strike_cache = {
    "NIFTY": [],
    "BANKNIFTY": [],
    "FINNIFTY": [],
    "last_updated": None
}

def find_high_priority_strikes(symbol="NIFTY"):
    """
    Identifies strikes with Delta between 0.59 and 0.69 (high priority range).
    Filters from the live option chain.
    
    Returns: List of strike data with symbol, LTP, delta, levels
    """
    priority_strikes = []
    
    try:
        # Fetch option chain for the symbol
        option_chain = nse_option_chain.get_option_chain(symbol)
        
        if not option_chain:
            logger.warning(f"Could not fetch option chain for {symbol}")
            return priority_strikes
        
        # Process both CE and PE
        for option_type in ["CE", "PE"]:
            for strike in option_chain.get(option_type, []):
                delta = strike.get('delta', 0)
                
                # Filter for priority delta range (0.59-0.69)
                if 0.59 <= delta <= 0.69:
                    high_915 = strike.get('high_915', 0)
                    low_915 = strike.get('low_915', 0)
                    
                    # Calculate GVN levels for this strike
                    levels = gvn_levels_engine.calculate_gvn_levels(high_915, low_915)
                    
                    priority_strikes.append({
                        "symbol": f"{symbol}{strike.get('strike', '')}{option_type}",
                        "index": symbol,
                        "option_type": option_type,
                        "strike_price": strike.get('strike', 0),
                        "ltp": strike.get('ltp', 0),
                        "delta": delta,
                        "gamma": strike.get('gamma', 0),
                        "levels": levels,
                        "high_915": high_915,
                        "low_915": low_915,
                        "volume": strike.get('volume', 0),
                        "open_interest": strike.get('open_interest', 0),
                        "bid_ask_spread": abs(strike.get('bid', 0) - strike.get('ask', 0)),
                        "timestamp": datetime.datetime.now()
                    })
        
        # Sort by delta proximity to 0.64 (center of range)
        priority_strikes.sort(key=lambda x: abs(x['delta'] - 0.64))
        
        logger.info(f"✅ Found {len(priority_strikes)} priority strikes for {symbol}")
        return priority_strikes
    
    except Exception as e:
        logger.error(f"Error finding priority strikes for {symbol}: {e}")
        return priority_strikes

def monitor_delta_levels():
    """
    Core logic to identify which strike's level is becoming active first.
    Continuously monitors all high-priority strikes and returns those triggering levels.
    
    Returns: List of active triggers with strike info and triggered level
    """
    logger.info("📡 [GVN DELTA ENGINE] Monitoring High-Priority Strikes (Delta 0.59-0.69)...")
    
    active_triggers = []
    
    try:
        for index in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
            # Get priority strikes for this index
            priority_strikes = find_high_priority_strikes(index)
            
            if not priority_strikes:
                continue
            
            # Update cache
            priority_strike_cache[index] = priority_strikes
            
            # Check each strike for level triggers
            for strike_data in priority_strikes:
                levels = strike_data.get('levels', {})
                ltp = strike_data.get('ltp', 0)
                
                # Check if any level is being triggered (with tolerance)
                triggered_level = _check_level_trigger(ltp, levels)
                
                if triggered_level:
                    active_triggers.append({
                        "symbol": strike_data['symbol'],
                        "index": index,
                        "triggered_level": triggered_level['level'],
                        "level_price": triggered_level['price'],
                        "current_price": ltp,
                        "delta": strike_data['delta'],
                        "strike_price": strike_data['strike_price'],
                        "option_type": strike_data['option_type'],
                        "volume": strike_data['volume'],
                        "bid_ask_spread": strike_data['bid_ask_spread'],
                        "strength": _calculate_trigger_strength(strike_data),
                        "timestamp": datetime.datetime.now()
                    })
        
        priority_strike_cache["last_updated"] = datetime.datetime.now()
        
        if active_triggers:
            logger.info(f"⚡ Found {len(active_triggers)} active level triggers")
        
        return active_triggers
    
    except Exception as e:
        logger.error(f"Error in monitor_delta_levels: {e}")
        return active_triggers

def _check_level_trigger(current_price, levels):
    """
    Validates if the current price is at an exact right level.
    Uses a 0.25 point tolerance for high precision.
    
    Returns: Dict with triggered level info or None
    """
    tolerance = 0.25
    
    # Priority order: tightest levels first
    level_priority = ['i5', 'i3', 'i2', 'i7', 'i6', 'i1', 'i0']
    
    for level_key in level_priority:
        level_price = levels.get(level_key, 0)
        
        if level_price > 0 and abs(current_price - level_price) <= tolerance:
            return {
                "level": level_key,
                "price": level_price,
                "distance": current_price - level_price
            }
    
    return None

def is_exact_right_level(strike_symbol, price, level_type):
    """
    Validates if the current reaction is at the EXACT right level.
    Uses 0.25 point tolerance for high precision.
    Also checks for volume confirmation.
    
    Returns: Boolean indicating if price is at exact level
    """
    try:
        # Get strike data from cache
        for index in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
            for strike in priority_strike_cache.get(index, []):
                if strike['symbol'] == strike_symbol:
                    levels = strike.get('levels', {})
                    level_price = levels.get(level_type, 0)
                    
                    if level_price > 0:
                        tolerance = 0.25
                        
                        # Check price proximity
                        price_match = abs(price - level_price) <= tolerance
                        
                        # Check volume confirmation (should be above average)
                        volume = strike.get('volume', 0)
                        volume_above_avg = volume > 1000  # Configurable threshold
                        
                        return price_match and volume_above_avg
        
        return False
    
    except Exception as e:
        logger.error(f"Error in is_exact_right_level: {e}")
        return False

def _calculate_trigger_strength(strike_data):
    """
    Calculates the strength/quality of a trigger signal.
    Considers delta proximity, volume, and bid-ask spread.
    
    Returns: Score 0-100 (higher = stronger signal)
    """
    try:
        delta = strike_data.get('delta', 0)
        volume = strike_data.get('volume', 0)
        spread = strike_data.get('bid_ask_spread', 0)
        
        # Delta score (0.64 is optimal, 0.59-0.69 is range)
        delta_score = max(0, 100 * (1 - abs(delta - 0.64) / 0.05))
        
        # Volume score (higher volume = better liquidity)
        volume_score = min(100, volume / 1000 * 100) if volume > 0 else 0
        
        # Spread score (lower spread = better)
        spread_score = max(0, 100 * (1 - spread / 1.0))
        
        # Weighted average
        strength = (delta_score * 0.4) + (volume_score * 0.4) + (spread_score * 0.2)
        
        return round(strength, 2)
    
    except:
        return 50  # Default mid-range if calculation fails

def get_top_priority_strikes(index, limit=5):
    """
    Returns the top N priority strikes sorted by trigger strength.
    """
    try:
        triggers = monitor_delta_levels()
        index_triggers = [t for t in triggers if t['index'] == index]
        index_triggers.sort(key=lambda x: x['strength'], reverse=True)
        return index_triggers[:limit]
    except:
        return []
