import datetime

def analyze_market_sentiment(ltp, open_p, high, low, volume, avg_volume, buy_vol, sell_vol):
    """
    GVN AI Market Analysis Engine v2.0 - Level Priority Edition
    """
    # 1. Volume Flow
    vol_ratio = buy_vol / (sell_vol if sell_vol > 0 else 1)
    delta_flow = buy_vol - sell_vol
    flow_text = "BUYERS CONTROL 🟢" if delta_flow > 0 else "SELLERS CONTROL 🔴"
    
    # 2. Market Mode
    mode = "SIDEWAYS"
    if vol_ratio > 1.2 and ltp > open_p: mode = "BULLISH 🟢"
    elif vol_ratio < 0.8 and ltp < open_p: mode = "BEARISH 🔴"
        
    # 3. Time Zone Momentum (IST)
    now = datetime.datetime.now()
    time_val = now.hour + (now.minute / 60.0)
    is_expiry = (now.weekday() == 3) # Thursday
    
    zone_status = "DULL ZONE (Wait ⚠️)"
    if 9.4 <= time_val <= 10.5:
        zone_status = "MORNING MOMENTUM 🟢" if delta_flow > 0 else "MORNING DOWN 🔴"
    elif 13.5 <= time_val <= 15.0:
        zone_status = "BREAKOUT UP 🚀" if delta_flow > 0 else "BREAKOUT DOWN 🩸"
        
    # 4. LEVEL PRIORITY LOGIC (As per Venkat's Request)
    priority_msg = "Scan i5 Level (P1)"
    if is_expiry:
        priority_msg = "EXPIRY MODE: Watch i1 (Z-to-H)"
    else:
        # Normal Day Priority
        priority_msg = "P1: i5 Momentum | P2: i7 Entry"
        
    inst_text = "📊 Normal Volume"
    if volume > (avg_volume * 2.5):
        inst_text = "🚨 BIG BOYS BUYING" if delta_flow > 0 else "🚨 BIG BOYS SELLING"
        
    return {
        "mode": mode,
        "vol_ratio": round(vol_ratio, 2),
        "zone": zone_status,
        "inst": inst_text,
        "flow": flow_text,
        "priority": priority_msg
    }
