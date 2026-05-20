import os
import requests
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import shared_data

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("915_Recovery")

class GVN_915_Recover:
    """Fetches 9:15 candle data even if the app started late"""
    
    def __init__(self, td_api):
        self.td_api = td_api

    def recover_benchmarks(self):
        logger.info("🔄 Starting 09:15 AM Benchmark Recovery...")
        indices = ["NIFTY", "SENSEX", "FINNIFTY"]
        
        # Today's date in TrueData format: YYMMDD
        today_str = datetime.now().strftime("%y%m%d")
        from_dt = f"{today_str}091500"
        to_dt = f"{today_str}092000"
        
        recovered_count = 0
        for symbol in indices:
            # Map index symbols for TrueData
            td_symbol = symbol
            if symbol == "NIFTY": td_symbol = "NIFTY 50"
            elif symbol == "BANKNIFTY": td_symbol = "NIFTY BANK"
            
            try:
                hist = self.td_api.get_historical_data(td_symbol, from_dt, to_dt)
                if hist and 'candles' in hist and len(hist['candles']) > 0:
                    candle = hist['candles'][0] # 9:15 candle
                    high = float(candle[2])
                    low = float(candle[3])
                    
                    shared_data.gvn_915_benchmark[symbol] = {
                        "high": high,
                        "low": low,
                        "captured": True,
                        "date": datetime.now().date().isoformat()
                    }
                    logger.info(f"✅ Recovered 9:15 for {symbol}: High={high}, Low={low}")
                    recovered_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to recover {symbol}: {e}")
                
        # 🌟 Option Strikes 9:15 AM Candle Recovery & Recording
        nifty_bench = shared_data.gvn_915_benchmark.get("NIFTY")
        if nifty_bench and nifty_bench.get("high", 0) > 0:
            spot = (nifty_bench["high"] + nifty_bench["low"]) / 2.0
            atm = round(spot / 50.0) * 50
            
            # Select 5 Call and 5 Put strikes around ATM
            # e.g., ATM-100, ATM-50, ATM, ATM+50, ATM+100
            strikes = [atm - 100, atm - 50, atm, atm + 50, atm + 100]
            
            try:
                from nse_option_chain import save_recorded_915_ohlc, get_truedata_option_symbol
                
                logger.info(f"🔄 Recovering option strike 9:15 candles around ATM={atm}...")
                
                # Save Nifty Spot to recorded JSON file as well
                save_recorded_915_ohlc("NIFTY_SPOT", nifty_bench["high"], nifty_bench["low"])
                
                for strike in strikes:
                    for opt_type in ["CE", "PE"]:
                        strike_key = f"{strike} {opt_type}"
                        try:
                            td_opt_symbol = get_truedata_option_symbol("NIFTY", strike, opt_type)
                            hist = self.td_api.get_historical_data(td_opt_symbol, from_dt, to_dt)
                            candles = []
                            if isinstance(hist, list):
                                candles = hist
                            elif isinstance(hist, dict):
                                candles = hist.get('candles') or hist.get('records') or hist.get('data') or hist.get('Records') or []
                                
                            if candles and len(candles) > 0:
                                highs = [float(c[2]) for c in candles if len(c) > 3]
                                lows = [float(c[3]) for c in candles if len(c) > 3]
                                if highs and lows:
                                    high = max(highs)
                                    low = min(lows)
                                    save_recorded_915_ohlc(strike_key, high, low)
                                    logger.info(f"✅ Recovered and recorded {strike_key} 9:15 AM candle: High={high}, Low={low}")
                        except Exception as e:
                            logger.error(f"❌ Failed to recover option {strike_key}: {e}")
            except Exception as e:
                logger.error(f"❌ Failed to load nse_option_chain functions for option recovery: {e}")
                
        return recovered_count > 0

if __name__ == "__main__":
    from truedata_rest_api import TrueDataRestAPI
    api = TrueDataRestAPI(os.getenv("TRUEDATA_USERNAME"), os.getenv("TRUEDATA_PASSWORD"))
    recoverer = GVN_915_Recover(api)
    recoverer.recover_benchmarks()
    print("Recovery Done. Current Benchmarks:", shared_data.gvn_915_benchmark)
