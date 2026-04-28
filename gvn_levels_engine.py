import math
import datetime

def calculate_master_levels(high5m, low5m):
    """
    Calculates the 'Holy Grail' GVN Master Levels based on 5-Minute 9:15 AM candle.
    These levels remain fixed for the rest of the day for the specific strike.
    """
    try:
        base_high = float(high5m)
        base_low = float(low5m)
        
        base_diff = base_high - base_low
        base_mid = base_diff / 2
        
        n1 = base_high + base_mid
        n2 = base_low + base_mid
        
        # GVN Base Calculations
        gvn0 = n2 * 0.118 / 0.5
        gvn100 = n1 * 0.786 / 0.5
        gvn_r = gvn100 - gvn0
        
        # The Master Level Map
        levels = {
            "i0": round(gvn0, 2),
            "i1": round(gvn100, 2),
            "i2": round(gvn0 + 0.763 * gvn_r, 2),
            "i3": round(gvn0 + 0.618 * gvn_r, 2),
            "i5": round(gvn0 + 0.5 * gvn_r, 2), # 0.5 Level
            "i6": round(gvn0 + 0.382 * gvn_r, 2), # 0.382 Level
            "i7": round(gvn0 + 0.220 * gvn_r, 2),
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "base_h": base_high,
            "base_l": base_low
        }
        return levels
    except Exception as e:
        print(f"[GVN ENGINE ERROR] Master Calculation Failed: {e}")
        return None

def track_live_movement(symbol, current_price, levels, last_signal=None):
    """
    Monitors 1-minute / Tick data against the 5-minute Master Levels.
    Detects breakouts and fast target completions.
    """
    if not levels: return None
    
    cp = float(current_price)
    buffer = 0.25 # Tight precision for fast moves
    
    signal = None
    
    # 1. 1st Entry (i5 Breakout) -> Fast Move to i3 or i2
    if cp > (levels['i5'] + buffer) and cp < levels['i3']:
        if last_signal != "i5_BUY":
            signal = {"type": "i5_BUY", "entry": levels['i5'], "targets": [levels['i3'], levels['i2']]}
            
    # 2. 2nd Entry (i7 Breakout) -> Fast Move to i6 or i5
    elif cp > (levels['i7'] + buffer) and cp < levels['i6']:
         if last_signal != "i7_BUY":
            signal = {"type": "i7_BUY", "entry": levels['i7'], "targets": [levels['i6'], levels['i5']]}
            
    # 3. Z to H (i0 Breakout) -> Massive move tracking
    elif cp > (levels['i0'] + buffer) and cp < levels['i7']:
        if last_signal != "Z_TO_H":
            signal = {"type": "Z_TO_H", "entry": levels['i0'], "targets": [levels['i7'], levels['i6'], levels['i5']]}
            
    # 4. Fast Target Completion Check (e.g. hitting i6 from i7 or i3 from i5)
    if last_signal == "i5_BUY" and cp >= levels['i3']:
        return {"status": "TARGET_REACHED", "target": "i3", "pnl": round(cp - levels['i5'], 2)}
        
    if last_signal == "i7_BUY" and cp >= levels['i6']:
        return {"status": "TARGET_REACHED", "target": "i6", "pnl": round(cp - levels['i7'], 2)}

    return signal
