import math

def calculate_gvn_levels(high_915, low_915):
    """
    Calculates GVN Master Levels (i0-i7) based on the 9:15 AM candle.
    """
    if not high_915 or not low_915:
        return None
        
    diff = high_915 - low_915
    result = diff / 2
    
    n1 = high_915 + result
    n2 = low_915 + result
    
    # GVN Constants from Pine Script
    gvn0_calc = n2 * 0.118 / 0.5
    gvn_i1_calc = n1 * 0.786 / 0.5
    
    spread = gvn_i1_calc - gvn0_calc
    
    levels = {
        "i0": round(gvn_i1_calc, 2),
        "i1": round(gvn0_calc, 2),
        "i2": round(gvn0_calc + 0.763 * spread, 2),
        "i3": round(gvn0_calc + 0.618 * spread, 2),
        "i5": round(gvn0_calc + 0.5 * spread, 2),
        "i6": round(gvn0_calc + 0.382 * spread, 2),
        "i7": round(gvn0_calc + 0.220 * spread, 2),
        "sl": 12 # Default SL as per script
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
