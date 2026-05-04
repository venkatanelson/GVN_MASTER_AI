
import os
import json
import time
import logging
from datetime import datetime
import shared_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_DataLab")

DATA_FILE = "gvn_expiry_study.json"

class GVNDataLab:
    """
    GVN Data Lab - Expiry to Expiry Analysis
    - Records Greeks (Delta, Gamma, Theta, Rho)
    - Records OI & % Change
    - Logs i-Level interactions
    - Auto-deletes data every Expiry Thursday at 6:00 PM
    """
    
    def __init__(self):
        self.last_clean_day = None

    def record_market_snapshot(self, strike_data, levels):
        """Saves current market state for post-expiry review"""
        try:
            snapshot = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "strike": strike_data['strike'],
                "type": strike_data['type'],
                "ltp": strike_data['ltp'],
                "delta": strike_data.get('delta', 0),
                "gamma": strike_data.get('gamma', 0),
                "theta": strike_data.get('theta', 0),
                "oi": strike_data.get('oi', 0),
                "levels": levels
            }
            
            data = []
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
            
            data.append(snapshot)
            
            # Keep only the last 1000 snapshots to prevent file bloat
            with open(DATA_FILE, "w") as f:
                json.dump(data[-1000:], f, indent=4)
                
            logger.info(f"📊 [DataLab] Recorded snapshot for {strike_data['strike']} {strike_data['type']}")
            self._check_and_cleanup()
            
        except Exception as e:
            logger.error(f"❌ DataLab Recording Error: {e}")

    def _check_and_cleanup(self):
        """Auto-deletes data on Expiry Day (Thursday) at 6 PM"""
        now = datetime.now()
        # Thursday is weekday 3, and time is after 18:00 (6 PM)
        if now.weekday() == 3 and now.hour >= 18:
            if self.last_clean_day != now.date():
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
                    logger.warning("🧹 [DataLab] Expiry cleanup complete. Starting fresh for next week!")
                    self.last_clean_day = now.date()

if __name__ == "__main__":
    lab = GVNDataLab()
    # Mock record for testing
    lab.record_market_snapshot({"strike": 24000, "type": "CE", "ltp": 150, "delta": 0.6}, {"i7": 130, "i5": 200})
