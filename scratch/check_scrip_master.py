import json
from datetime import datetime, timedelta
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_resolved_expiries():
    print("=== RESOLVING EXPIRIES FOR SYMBOLS ===")
    
    # Load angel scrip master if available
    master_data = []
    if os.path.exists("angel_scrip_master.json"):
        print("Loading angel_scrip_master.json...")
        try:
            with open("angel_scrip_master.json", "r", encoding="utf-8") as f:
                master_data = json.load(f)
            print(f"Loaded {len(master_data)} scrips.")
        except Exception as e:
            print("Error loading scrip master:", e)
            
    today_date = datetime.now().date()
    print("Today's Date according to Python:", today_date)
    print("Today's Weekday (0=Mon, 1=Tue, 3=Thu, etc.):", today_date.weekday())
    
    symbols = ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"]
    for symbol in symbols:
        symbol_upper = symbol.upper()
        expiry_dt = None
        
        # 1. Try to find the closest expiry in the future or today from the scrip master
        try:
            exp_dates = []
            for item in master_data:
                # Angel master usually uses name format e.g. NIFTY
                if item.get('name') == symbol_upper and item.get('expiry') and item.get('exch_seg') in ['NFO', 'BFO']:
                    try:
                        exp_dt_obj = datetime.strptime(item.get('expiry'), "%d%b%Y")
                        if exp_dt_obj.date() >= today_date:
                            exp_dates.append(exp_dt_obj)
                    except:
                        pass
            if exp_dates:
                expiry_dt = min(exp_dates)
                print(f"Scrip Master found for {symbol}: closest expiry = {expiry_dt.strftime('%Y-%m-%d')}")
        except Exception as ex:
            print(f"Error resolving from scrip master for {symbol}: {ex}")
            
        # 2. Hardcoded fallback if scrip master lookup failed
        if not expiry_dt:
            today = datetime.now()
            # Thursday (3) for Nifty/Banknifty/Finnifty, Friday (4) for Sensex
            if "SENSEX" in symbol_upper:
                target_day = 4
            elif "FINNIFTY" in symbol_upper:
                target_day = 1 # Tuesday (1)
            else:
                target_day = 3
            days_ahead = target_day - today.weekday()
            if days_ahead < 0 or (days_ahead == 0 and today.time() >= datetime.strptime("15:30:00", "%H:%M:%S").time()):
                days_ahead += 7
            expiry_dt = today + timedelta(days=days_ahead)
            print(f"Fallback used for {symbol}: closest expiry = {expiry_dt.strftime('%Y-%m-%d')}")
            
        is_expiry = (expiry_dt.date() == today_date)
        print(f"Is today expiry day for {symbol}? {is_expiry}\n")

if __name__ == "__main__":
    import os
    check_resolved_expiries()
