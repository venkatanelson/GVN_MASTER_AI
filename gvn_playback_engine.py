import pandas as pd

import time
import json
import os
from datetime import datetime
import shared_data
from nse_option_chain import analyze_and_update_gvn_scanner, dhan_master_config

CSV_PATH = "live_market_history.csv"

def run_playback(speed=1.0, symbol="NIFTY"):
    """
    Dynamically generates live market ticks to demonstrate the GVN Master Algo.
    It simulates a Breakout, a Signal Generation, and a Target Hit!
    """
    print(f"🎬 Starting GVN Playback for {symbol} at {speed}x speed...")
    msg = f"🎬 Starting GVN Dynamic Demo for {symbol} at {speed}x speed..."
    try: shared_data.demo_logs.append(msg)
    except: pass
    
    # Base configuration for different symbols
    base_spots = {"NIFTY": 24100, "BANKNIFTY": 54800, "FINNIFTY": 21400, "SENSEX": 79500, "MCX": 6800}
    spot = base_spots.get(symbol, 10000)
    
    # Set 9:15 Benchmark just above current spot to simulate a breakout
    shared_data.gvn_915_benchmark[symbol] = {"high": spot + 10, "low": spot - 50}
    
    strike = spot
    opt_ltp = 100.0
    
    for step in range(1, 25): # 24 steps of simulation
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Slowly increase the spot and option price
        spot += 1.5 
        opt_ltp += 1.2
        
        # Push to dashboard
        shared_data.market_data[symbol] = round(spot, 2)
        time_msg = f"⏰ {ts} | 📊 {symbol} SPOT: ₹{round(spot, 2)} | {strike} CE LTP: ₹{round(opt_ltp, 2)}"
        try: shared_data.demo_logs.append(time_msg)
        except: pass
        
        # Build mock data for the analyzer
        formatted_data = [{
            "strike": strike,
            "CE": {
                "lastTradedPrice": opt_ltp,
                "changeinOpenInterest": 50000 + (step * 1000),
                "totalTradedVolume": 200000 + (step * 5000),
                "delta": 0.62,  # Fixed Delta 60 for demo
                "impliedVolatility": 18.5
            },
            "PE": {}
        }]
        
        mock_data = {
            "records": {"underlyingValue": spot, "expiryDates": ["19-May-2026"], "data": formatted_data},
            "source": f"DEMO_{ts}",
            "spot": spot
        }
        # Call the core logic
        try:
            analyze_and_update_gvn_scanner(symbol, mock_external_data=mock_data)
        except Exception as e:
            err_msg = f"❌ [DEMO CRASH] {e}"
            print(err_msg)
            try: shared_data.demo_logs.append(err_msg)
            except: pass
            
        # Optional: Print to confirm loop is alive
        print(f"[DEBUG] Step {step} completed successfully.")
        
        # Stop early if the trade is done (active flipped back to False means target/sl hit)
        if step > 5 and not shared_data.demo_trade.get("active") and shared_data.demo_trade.get("symbol"):
            break
            
        time.sleep(1.5 / speed)

    msg = "🏁 Demo Playback Completed."
    try: shared_data.demo_logs.append(msg)
    except: pass
    dhan_master_config['active'] = True

if __name__ == "__main__":
    run_playback(speed=2.0)
