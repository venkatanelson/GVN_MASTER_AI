import datetime
import time
import shared_data
import random

# ---------------------------------------------------------
# GVN AI ENGINE LOGIC (EMBEDDED TO PREVENT MODULE NOT FOUND)
# ---------------------------------------------------------
def analyze_market_sentiment(ltp, open_p, high, low, volume, avg_volume, buy_vol, sell_vol, ma_200=23518, usd_inr=95.74):
    vol_ratio = buy_vol / (sell_vol if sell_vol > 0 else 1)
    delta_flow = buy_vol - sell_vol
    flow_text = "BUYERS CONTROL 🟢" if delta_flow > 0 else "SELLERS CONTROL 🔴"
    
    # 🚨 TRAP DETECTION
    trap_status = "Safe"
    if abs(ltp - ma_200) < 15:
        if 0.9 <= vol_ratio <= 1.1:
            trap_status = "🚨 TRAP ZONE: Big Players holding at 200 MA."
        else:
            trap_status = "Battle at 200 MA."

    mode = "SIDEWAYS"
    if vol_ratio > 1.3 and ltp > open_p: mode = "BULLISH 🟢"
    elif vol_ratio < 0.7 and ltp < open_p: mode = "BEARISH 🔴"
    
    # Premium Eating Check
    if abs(ltp - open_p) < 25 and volume < (avg_volume * 0.8):
        mode = "⚠️ PREMIUM EATING 📉"
        
    now = datetime.datetime.now()
    time_val = now.hour + (now.minute / 60.0)
    is_expiry = (now.weekday() in [3, 2])
    
    zone_status = "DULL ZONE (Wait ⚠️)"
    if 9.4 <= time_val <= 10.5:
        zone_status = "MORNING MOMENTUM 🟢" if delta_flow > 0 else "MORNING DOWN 🔴"
    elif 13.5 <= time_val <= 15.0:
        zone_status = "BREAKOUT UP 🚀" if delta_flow > 0 else "BREAKOUT DOWN 🩸"
        
    priority_msg = "P1: i5 Momentum | P2: i7 Entry"
    if is_expiry: priority_msg = "EXPIRY MODE: Watch i1 (Z-to-H)"
    if mode == "⚠️ PREMIUM EATING 📉": priority_msg = "🚨 EXIT OTM: Theta Risk!"
        
    inst_text = "📊 Normal Volume"
    if volume > (avg_volume * 2.5):
        inst_text = "🚨 BIG BOYS BUYING" if delta_flow > 0 else "🚨 BIG BOYS SELLING"
        
    return {
        "mode": mode, "vol_ratio": round(vol_ratio, 2), "zone": zone_status,
        "inst": inst_text, "flow": flow_text, "priority": priority_msg,
        "trap": trap_status, "currency": f"INR {usd_inr}"
    }

# ---------------------------------------------------------
# SHOONYA LIVE FEED ENGINE
# ---------------------------------------------------------
def process_shoonya_feed():
    print("🛰️ [SHOONYA FEED] Starting Master AI Engine...")
    from app import app, db, UserBrokerConfig, User, cipher
    
    with app.app_context():
        # Get Credentials
        config = UserBrokerConfig.query.first()
        if not config:
            print("⚠️ [AUTO-LOGIN] No credentials found.")
            return

        print(f"✅ [AUTO-LOGIN] Credentials found for {config.client_id}")
        
        # MOCK LIVE FEED LOOP REMOVED TO ALLOW REAL DATA FROM AI ENGINE
        print("✅ [LIVE FEED] Handing over data updates to GVN AI Master Engine...")
        while True:
            time.sleep(10) # Just keep thread alive if needed


def start_live_feed_worker():
    import threading
    thread = threading.Thread(target=process_shoonya_feed, daemon=True)
    thread.start()
    print("🛰️ [SHOONYA] Live Feed Worker Started in Background Thread.")
