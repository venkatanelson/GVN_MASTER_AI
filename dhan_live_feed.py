import datetime
import time
import threading
import requests
import shared_data
import gvn_levels_engine
import random

# DHAN LIVE FEED ENGINE v2.6 (Enhanced Debugging)

dhan_master_config = {
    "client_id": None, "access_token": None, "broker_name": "Dhan", "active": False
}

def fetch_dhan_spot_data(symbol="NIFTY"):
    # 1. Try Dhan API
    if dhan_master_config.get("active") and dhan_master_config.get("access_token"):
        try:
            from dhanhq import dhanhq
            dhan = dhanhq(dhan_master_config["client_id"], dhan_master_config["access_token"])
            sec_ids = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27", "SENSEX": "1"}
            sid = sec_ids.get(symbol)
            if sid:
                instruments = {"IDX_I": [sid]}
                quote = dhan.quote_data(instruments)
                if quote.get('status') == 'success':
                    price = quote.get('data', {}).get(sid, {}).get('lastPrice', 0)
                    if price > 0: return float(price)
        except Exception as e:
            print(f"⚠️ [DHAN API FAIL] {e}")

    # 2. Try Yahoo Finance (Fallback)
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        tickers = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "NIFTY-FIN-SERVICE.NS", "SENSEX": "^BSESN"}
        ticker = tickers.get(symbol, "^NSEI")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            price = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
            if price > 0: return price
    except Exception as e:
        print(f"⚠️ [YAHOO FAIL] {symbol}: {e}")
    
    # 3. Simulator Mode (Only if everything fails, so user sees something)
    # return round(24250.0 + random.uniform(-10, 10), 2) if symbol == "NIFTY" else 0
    return 0

def fetch_strike_ltp(symbol_name):
    spot = shared_data.live_option_chain_summary.get("NIFTY", {}).get("spot", 0)
    if spot == 0: return 0
    try:
        strike_val = int(''.join(filter(str.isdigit, symbol_name)))
        diff = abs(spot - strike_val)
        base_price = max(10, 300 - diff) 
        return round(base_price + random.uniform(-5, 5), 2)
    except: return 0

def process_strike_levels():
    print("🛰️ [GVN SCANNER] Initializing Professional Alpha Grid...")
    from app import app, db, UserBrokerConfig, MarketData, cipher
    
    while True:
        try:
            # Sync Config every loop to handle user updates
            with app.app_context():
                config = UserBrokerConfig.query.first()
                if config:
                    dhan_master_config["client_id"] = config.client_id
                    try:
                        if config.encrypted_access_token:
                            dhan_master_config["access_token"] = cipher.decrypt(config.encrypted_access_token).decode()
                            dhan_master_config["active"] = True
                    except: pass

            for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                spot = fetch_dhan_spot_data(symbol)
                if spot > 0:
                    print(f"✅ [DATA] {symbol} Spot: {spot}")
                    if symbol not in shared_data.live_option_chain_summary:
                        shared_data.live_option_chain_summary[symbol] = {"spot": 0}
                    shared_data.live_option_chain_summary[symbol]["spot"] = spot
                    
                    with app.app_context():
                        md = MarketData.query.filter_by(symbol=symbol).first()
                        if not md: md = MarketData(symbol=symbol); db.session.add(md)
                        md.price = spot
                        md.last_updated = datetime.datetime.utcnow()
                        db.session.commit()

                    shared_data.broker_connection_status.update({
                        "connected": True,
                        "broker_name": "Universal",
                        "last_checked": datetime.datetime.now().strftime("%H:%M:%S")
                    })
                else:
                    print(f"❌ [DATA FAIL] {symbol} is 0. Check Internet.")
                    shared_data.broker_connection_status["connected"] = False

            time.sleep(2)
        except Exception as e:
            print(f"❌ [CRITICAL ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    process_strike_levels()
