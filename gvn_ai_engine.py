import datetime

def analyze_market_sentiment(ltp, open_p, high, low, volume, avg_volume, buy_vol, sell_vol, ma_200=None, usd_inr=None):
    """
    GVN AI Market Analysis Engine v3.0 - Trap & Momentum Edition
    Logic: Venkat's GVN Market Formula (Version 1.0)
    """
    # 1. Volume Flow & Ratio
    vol_ratio = buy_vol / (sell_vol if sell_vol > 0 else 1)
    delta_flow = buy_vol - sell_vol
    flow_text = "BUYERS CONTROL 🟢" if delta_flow > 0 else "SELLERS CONTROL 🔴"
    
    # 2. Institutional Trap Detection (The "Dark Secret" Logic)
    trap_status = "Safe"
    if ma_200 and abs(ltp - ma_200) < 15:
        if 0.9 <= (buy_vol / (sell_vol if sell_vol > 0 else 1)) <= 1.1:
            trap_status = "🚨 TRAP ZONE: Big Players holding market at 200 MA. No expansion."
        else:
            trap_status = "Barrier Battle: Fight near 200 MA."

    # 3. Currency Impact (USD/INR Pressure)
    currency_impact = "Normal"
    if usd_inr and usd_inr > 95.0:
        currency_impact = f"⚠️ HIGH PRESSURE: Rupee at {usd_inr}. Selling Bias Strong."

    # 4. Market Mode & Premium Eating Logic
    mode = "SIDEWAYS"
    if vol_ratio > 1.3 and ltp > open_p: 
        mode = "BULLISH 🟢"
    elif vol_ratio < 0.7 and ltp < open_p: 
        mode = "BEARISH 🔴"
    
    # Detect Premium Eating Zone (Range Bound + Slow Volume)
    is_premium_eating = False
    if abs(ltp - open_p) < 20 and volume < (avg_volume * 0.8):
        is_premium_eating = True
        mode = "⚠️ PREMIUM EATING ZONE (Theta Decay Trap)"

    # 5. Time Zone Momentum (IST)
    now = datetime.datetime.now()
    time_val = now.hour + (now.minute / 60.0)
    is_expiry = (now.weekday() in [3, 2]) # Thursday or Wednesday
    
    zone_status = "DULL ZONE (Wait ⚠️)"
    if 9.4 <= time_val <= 10.5:
        zone_status = "MORNING MOMENTUM 🟢" if delta_flow > 0 else "MORNING DOWN 🔴"
    elif 13.5 <= time_val <= 15.0:
        zone_status = "BREAKOUT UP 🚀" if delta_flow > 0 else "BREAKOUT DOWN 🩸"
        
    # 6. Priority Messaging
    priority_msg = "Scan i5 Level (P1)"
    if is_expiry:
        priority_msg = "EXPIRY MODE: Watch i1 (Zero-to-Hero)"
        if is_premium_eating:
            priority_msg = "🚨 EXIT OTM: Theta is eating your premium!"
    
    inst_text = "📊 Normal Volume"
    if volume > (avg_volume * 2.5):
        inst_text = "🚨 BIG BOYS BUYING" if delta_flow > 0 else "🚨 BIG BOYS SELLING"
        
    return {
        "mode": mode,
        "vol_ratio": round(vol_ratio, 2),
        "zone": zone_status,
        "inst": inst_text,
        "flow": flow_text,
        "priority": priority_msg,
        "trap": trap_status,
        "currency": currency_impact
    }
