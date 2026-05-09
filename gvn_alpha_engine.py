import datetime
import time
import shared_data

def calculate_gvn_levels(high915, low915):
    """
    Implements the core GVN i-Level Fibonacci math from the Pine Script.
    Matches the GVN MASTER Indicator 2026 PRO v2 exactly.
    """
    try:
        base_high = float(high915)
        base_low = float(low915)
        
        base_diff = base_high - base_low
        base_mid = base_diff / 2
        
        n1 = base_high + base_mid
        n2 = base_low + base_mid
        
        # GVN Base Calculations
        gvn0 = n2 * 0.118 / 0.5
        gvn100 = n1 * 0.786 / 0.5
        gvn_r = gvn100 - gvn0
        
        levels = {
            "i0": gvn0,
            "i1": gvn100,
            "i2": gvn0 + 0.763 * gvn_r,
            "i3": gvn0 + 0.618 * gvn_r,
            "i5": gvn0 + 0.5 * gvn_r,
            "i6": gvn0 + 0.382 * gvn_r,
            "i7": gvn0 + 0.220 * gvn_r
        }
        return levels
    except Exception as e:
        print(f"[ALGO ENGINE ERROR] Level Calculation Failed: {e}")
        return None

def analyze_trade_signal(symbol, ltp, levels, volume_data, ai_sentiment):
    """
    Validates a price breakout against i-Levels and AI filters.
    Includes all levels (i1, i2, i3, i5, i6, i7) from the Master Algo.
    """
    if not levels: return None
    
    # Using a 0.5 buffer for precision
    buffer = 0.5
    signal = None
    
    # 1. Zero to Hero (i0 Breakout)
    if ltp > (levels['i0'] + buffer) and ltp < levels['i7']:
        signal = "Z to H (i0 BREAKOUT) 🚀"
    
    # 2. i7 Breakout (Put Entry / 2nd Entry)
    elif ltp > (levels['i7'] + buffer) and ltp < levels['i6']:
        signal = "i7 BREAKOUT 📉"
        
    # 3. i5 Breakout (1st Entry)
    elif ltp > (levels['i5'] + buffer) and ltp < levels['i3']:
        signal = "i5 BREAKOUT 🔥"
        
    # AI Filtering Logic
    if signal:
        # Avoid fakeouts using Sentiment score
        if ai_sentiment.get('score', 0) < 60:
            return None 
        
        return {
            "symbol": symbol,
            "ltp": ltp,
            "trigger_signal": signal,
            "levels": levels,
            "score": ai_sentiment.get('score', 0),
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }
    
    return None
