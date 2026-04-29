import datetime
import time
import threading
import requests
import shared_data
import gvn_levels_engine
import gvn_ai_engine
import random
import os
from dotenv import load_dotenv
load_dotenv()

# SHOONYA LIVE FEED ENGINE v3.5 (AI PULSE & ALPHA GRID READY)

def trigger_alpha_grid_calculation(spot):
    print("🚀 [ALPHA GRID] Calculating 14-Strike Levels for Today...")
    # ... (rest of the logic remains same as v3.0)
    atm = round(spot / 50) * 50
    strikes = []
    for i in range(-3, 4):
        strike_val = atm + (i * 50)
        strikes.append({"symbol": f"NIFTY{strike_val}CE", "val": strike_val, "type": "CE"})
    for i in range(-3, 4):
        strike_val = atm + (i * 50)
        strikes.append({"symbol": f"NIFTY{strike_val}PE", "val": strike_val, "type": "PE"})
        
    mock_data = []
    for s in strikes:
        base_price = 100 if "CE" in s["symbol"] else 80
        high = base_price + random.uniform(5, 15)
        low = base_price - random.uniform(2, 5)
        mock_data.append({
            "symbol": s["symbol"],
            "high": round(high, 2), "low": round(low, 2), "delta": 0.65
        })
    shared_data.gvn_alpha_grid = gvn_levels_engine.process_alpha_grid(mock_data)

def process_shoonya_feed():
    print("🛰️ [SHOONYA FEED] Initializing Master Engine...")
    from app import app, db, UserBrokerConfig, MarketData, cipher
    
    grid_calculated_today = False

    while True:
        try:
            # Fetch Spot (Using fallback for now)
            spot = 24350.0 + random.uniform(-5, 5)
            if spot > 0:
                shared_data.market_data["NIFTY"] = spot
                
                # 🤖 Update GVN AI Sentiment
                # Using candle-based approximation as per Pine Script
                v = random.uniform(500, 2000)
                is_green = random.choice([True, False])
                sentiment = gvn_ai_engine.analyze_market_sentiment(
                    ltp=spot, open_p=spot-1, high=spot+2, low=spot-2,
                    volume=v, avg_volume=1000,
                    buy_vol=v if is_green else v*0.3,
                    sell_vol=0 if is_green else v*0.7
                )
                shared_data.market_pulse.update(sentiment)

                # Check for 9:16 AM Trigger
                now = datetime.datetime.now()
                if now.hour == 9 and now.minute == 16 and not grid_calculated_today:
                    trigger_alpha_grid_calculation(spot)
                    grid_calculated_today = True
                
                if not shared_data.gvn_alpha_grid: trigger_alpha_grid_calculation(spot)

                # Sync to DB
                with app.app_context():
                    md = MarketData.query.filter_by(symbol="NIFTY").first()
                    if not md: md = MarketData(symbol="NIFTY"); db.session.add(md)
                    md.price = spot; md.last_updated = datetime.datetime.utcnow()
                    db.session.commit()

            time.sleep(1)
        except Exception as e:
            print(f"⚠️ [FEED ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    process_shoonya_feed()
