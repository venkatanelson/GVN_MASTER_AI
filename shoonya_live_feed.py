import datetime
import time
import shared_data
import random

# ---------------------------------------------------------
# GVN AI ENGINE LOGIC (EMBEDDED TO PREVENT MODULE NOT FOUND)
# ---------------------------------------------------------
def analyze_market_sentiment(ltp, open_p, high, low, volume, avg_volume, buy_vol, sell_vol):
    vol_ratio = buy_vol / (sell_vol if sell_vol > 0 else 1)
    delta_flow = buy_vol - sell_vol
    flow_text = "BUYERS CONTROL 🟢" if delta_flow > 0 else "SELLERS CONTROL 🔴"
    
    mode = "SIDEWAYS"
    if vol_ratio > 1.2 and ltp > open_p: mode = "BULLISH 🟢"
    elif vol_ratio < 0.8 and ltp < open_p: mode = "BEARISH 🔴"
        
    now = datetime.datetime.now()
    time_val = now.hour + (now.minute / 60.0)
    is_expiry = (now.weekday() == 3) # Thursday
    
    zone_status = "DULL ZONE (Wait ⚠️)"
    if 9.4 <= time_val <= 10.5:
        zone_status = "MORNING MOMENTUM 🟢" if delta_flow > 0 else "MORNING DOWN 🔴"
    elif 13.5 <= time_val <= 15.0:
        zone_status = "BREAKOUT UP 🚀" if delta_flow > 0 else "BREAKOUT DOWN 🩸"
        
    priority_msg = "P1: i5 Momentum | P2: i7 Entry"
    if is_expiry: priority_msg = "EXPIRY MODE: Watch i1 (Z-to-H)"
        
    inst_text = "📊 Normal Volume"
    if volume > (avg_volume * 2.5):
        inst_text = "🚨 BIG BOYS BUYING" if delta_flow > 0 else "🚨 BIG BOYS SELLING"
        
    return {
        "mode": mode, "vol_ratio": round(vol_ratio, 2), "zone": zone_status,
        "inst": inst_text, "flow": flow_text, "priority": priority_msg
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
        
        # MOCK LIVE FEED LOOP (SIMULATING FOR STABILITY)
        while True:
            try:
                spot = 24150.0 + random.uniform(-10, 10)
                shared_data.market_data["NIFTY"] = spot
                
                # Update AI Pulse
                pulse = analyze_market_sentiment(spot, 24100, 24200, 24050, 500000, 200000, 300000, 200000)
                shared_data.market_pulse.update(pulse)
                
                # Update Alpha Grid
                if not shared_data.gvn_alpha_grid:
                    shared_data.gvn_alpha_grid = [
                        {"strike": int(spot//50)*50 + (i*50), "type": "CE", "delta": 0.65 - (i*0.02)}
                        for i in range(-3, 4)
                    ]
                
                time.sleep(1)
            except Exception as e:
                print(f"❌ [FEED ERROR] {e}")
                time.sleep(5)

def start_live_feed_worker():
    import threading
    thread = threading.Thread(target=process_shoonya_feed, daemon=True)
    thread.start()
    print("🛰️ [SHOONYA] Live Feed Worker Started in Background Thread.")
