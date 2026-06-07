import time
import logging
import datetime
import sqlite3
import os
import sys

# Setup paths for standard modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import shared_data
import gvn_data_bank
from gvn_ai_wind_engine import GVNAiWindEngine
import nse_option_chain

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("gvn_wind_monitor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WindMonitorEngine")

def is_market_hours():
    """Checks if current time is within Indian market hours (09:15 to 15:30 IST, Monday-Friday)."""
    now = datetime.datetime.now()
    if now.weekday() >= 5:  # Weekend
        return False
    
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close

def run_wind_monitor_cycle():
    """Runs a single data gathering and wind calculation cycle for NIFTY and SENSEX."""
    logger.info("🌪️ Starting Wind Calculation Cycle...")
    
    # Ensure DB is initialized
    gvn_data_bank.init_db()
    
    wind_engine = GVNAiWindEngine()
    symbols = ["NIFTY", "SENSEX"]
    
    for symbol in symbols:
        try:
            logger.info(f"🔄 Fetching Option Chain data for {symbol}...")
            
            # Fetch option chain from nse_option_chain wrapper
            # For SENSEX, it will use BSE/Angel or emulated options chain based on spot price.
            exchange = "BSE" if symbol == "SENSEX" else "NSE"
            data = nse_option_chain.fetch_nse_option_chain(symbol, exchange=exchange)
            
            if not data or "records" not in data:
                logger.warning(f"⚠️ Empty/Null option chain data received for {symbol}. Skipping cycle.")
                continue
                
            records = data["records"]
            spot = records.get("underlyingValue", 0)
            if spot <= 0:
                spot = shared_data.market_data.get(symbol, 0)
            if spot <= 0:
                logger.warning(f"⚠️ Spot price is 0 for {symbol}. Skipping.")
                continue
                
            # Compile Option Chain metrics
            total_ce_oi = 0
            total_pe_oi = 0
            ce_vol = 0
            pe_vol = 0
            ce_coi = 0
            pe_coi = 0
            
            for item in records.get("data", []):
                if "CE" in item:
                    ce = item["CE"]
                    total_ce_oi += ce.get("openInterest", 0) or ce.get("oi", 0) or 0
                    ce_vol += ce.get("totalTradedVolume", 0) or ce.get("volume", 0) or 0
                    ce_coi += ce.get("changeinOpenInterest", 0) or ce.get("oi_change", 0) or 0
                if "PE" in item:
                    pe = item["PE"]
                    total_pe_oi += pe.get("openInterest", 0) or pe.get("oi", 0) or 0
                    pe_vol += pe.get("totalTradedVolume", 0) or pe.get("volume", 0) or 0
                    pe_coi += pe.get("changeinOpenInterest", 0) or pe.get("oi_change", 0) or 0
                    
            if total_ce_oi <= 0:
                total_ce_oi = 1  # Avoid division by zero
                
            pcr = round(total_pe_oi / total_ce_oi, 2)
            
            # Setup references
            ref_price = spot # Fallback reference price
            
            # --- DELTA-PREMIUM DIVERGENCE (DPD) DATA GATHERING ---
            atm_strike = None
            min_diff = float("inf")
            ce_ltp = 0.0
            pe_ltp = 0.0
            ce_delta = 0.50
            pe_delta = -0.50
            
            # Find closest strike price (ATM)
            for item in records.get("data", []):
                strike_price = item.get("strikePrice") or item.get("strike", 0)
                if strike_price > 0:
                    diff = abs(strike_price - spot)
                    if diff < min_diff:
                        min_diff = diff
                        atm_strike = strike_price
            
            # Extract ATM prices and deltas
            if atm_strike is not None:
                for item in records.get("data", []):
                    strike_price = item.get("strikePrice") or item.get("strike", 0)
                    if strike_price == atm_strike:
                        if "CE" in item:
                            ce = item["CE"]
                            ce_ltp = ce.get("lastPrice") or ce.get("lastTradedPrice", 0.0) or 0.0
                            ce_delta = ce.get("delta")
                            if ce_delta is None or ce_delta == 0:
                                try:
                                    iv = ce.get("impliedVolatility", 16.5) or 16.5
                                    sigma = iv / 100.0
                                    today = datetime.datetime.now()
                                    expiry_weekday = 4 if symbol == "SENSEX" else 3
                                    days_to_expiry = max(1, (expiry_weekday - today.weekday()) % 7)
                                    T = days_to_expiry / 365.0
                                    r = 0.07
                                    ce_delta = abs(nse_option_chain.calculate_delta(spot, strike_price, T, r, sigma, "CE"))
                                except:
                                    ce_delta = 0.5 - ((strike_price - spot) / spot)
                            ce_delta = min(0.99, max(0.01, abs(ce_delta)))
                            
                        if "PE" in item:
                            pe = item["PE"]
                            pe_ltp = pe.get("lastPrice") or pe.get("lastTradedPrice", 0.0) or 0.0
                            pe_delta = pe.get("delta")
                            if pe_delta is None or pe_delta == 0:
                                try:
                                    iv = pe.get("impliedVolatility", 16.5) or 16.5
                                    sigma = iv / 100.0
                                    today = datetime.datetime.now()
                                    expiry_weekday = 4 if symbol == "SENSEX" else 3
                                    days_to_expiry = max(1, (expiry_weekday - today.weekday()) % 7)
                                    T = days_to_expiry / 365.0
                                    r = 0.07
                                    pe_delta = -abs(nse_option_chain.calculate_delta(spot, strike_price, T, r, sigma, "PE"))
                                except:
                                    pe_delta = - (0.5 + ((strike_price - spot) / spot))
                            if pe_delta > 0:
                                pe_delta = -pe_delta
                            pe_delta = max(-0.99, min(-0.01, pe_delta))
                        break
            
            logger.info(f"🎯 ATM Strike for {symbol}: {atm_strike} | CE LTP: {ce_ltp} CE Delta: {ce_delta:.2f} | PE LTP: {pe_ltp} PE Delta: {pe_delta:.2f}")

            # Run Wind calculation
            dna = wind_engine.get_market_dna(
                symbol=symbol, ltp=spot, vwap=ref_price, 
                ce_oi=total_ce_oi, pe_oi=total_pe_oi,
                ce_coi=ce_coi, pe_coi=pe_coi,
                ce_vol=ce_vol, pe_vol=pe_vol,
                delta=ce_delta, gamma=0.015, theta=-0.5,
                ce_ltp=ce_ltp, pe_ltp=pe_ltp,
                ce_delta=ce_delta, pe_delta=pe_delta
            )
            
            wind_dir = dna["wind_engine"]["wind_state"]
            wind_power = dna["wind_engine"]["wind_power"]
            trend_type = dna["wind_engine"]["trend_type"]
            smart_money = dna["smart_money_status"]
            battle_status = dna["battle_status"]
            
            logger.info(f"📊 Wind Report for {symbol}: Spot={spot} | Wind={wind_dir} (Power={wind_power}) | PCR={pcr}")
            
            # Save to SQLite Database
            gvn_data_bank.save_wind_status(
                symbol=symbol,
                wind_dir=wind_dir,
                wind_power=wind_power,
                trend_type=trend_type,
                smart_money=smart_money,
                battle_status=battle_status,
                pcr=pcr,
                spot=spot
            )
            logger.info(f"💾 Wind state saved to Database for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error in wind monitoring cycle for {symbol}: {e}", exc_info=True)

def main():
    logger.info("="*60)
    logger.info("🌪️ GVN MASTER WIND MONITOR STARTING...")
    logger.info("="*60)
    
    # Perform startup scan regardless of market hours for sanity check
    run_wind_monitor_cycle()
    
    while True:
        try:
            if is_market_hours():
                run_wind_monitor_cycle()
            else:
                logger.debug("Market closed. Skipping wind cycle.")
                
            # Sleep for 180 seconds (3 minutes)
            time.sleep(180)
        except KeyboardInterrupt:
            logger.info("🛑 Wind Monitor stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
