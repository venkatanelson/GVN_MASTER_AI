import datetime
import time
import shared_data
import random
import logging
import threading
import requests
import pyotp
import json
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShoonyaLiveFeed")

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
# SHOONYA LIVE FEED ENGINE v3.0 (Dynamic Multi-User Sync)
# ---------------------------------------------------------
class ShoonyaLiveFeed:
    def __init__(self, client_id, password, api_secret, totp_key, vendor_code=None):
        self.client_id = client_id
        self.password = password
        self.api_secret = api_secret
        self.totp_key = totp_key
        self.vendor_code = vendor_code or client_id
        self.is_running = False
        self.token = None 
        self.last_login = 0

    def _sha256_hash(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_totp(self):
        if not self.totp_key: return ""
        try:
            return pyotp.TOTP(self.totp_key).now()
        except:
            return ""

    def _http_login_once(self):
        try:
            totp = self._get_totp()
            pwd_hash = self._sha256_hash(self.password)
            app_key_hash = self._sha256_hash(f"{self.client_id}|{self.api_secret}")
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0'
            }
            payload = {
                "apkversion": "1.0.0",
                "uid": self.client_id,
                "pwd": pwd_hash,
                "twofa": totp,
                "vc": self.vendor_code,
                "appkey": app_key_hash,
                "imei": "abc1234",
                "source": "API"
            }
            jData = "jData=" + json.dumps(payload)
            resp = requests.post("https://api.shoonya.com/NorenWClientTP/QuickAuth", data=jData, headers=headers, timeout=12)
            
            if resp.status_code == 200:
                rj = resp.json()
                if rj.get('stat') == 'Ok':
                    self.token = rj.get('susertoken')
                    self.last_login = time.time()
                    logger.info("✅ Shoonya Session Established successfully")
                    return True
            logger.error(f"❌ Shoonya Login Failed: {resp.text[:100]}")
        except Exception as e:
            logger.error(f"❌ Shoonya Login Error: {e}")
        return False

    def fetch_ltp_direct(self):
        if not self.token or (time.time() - self.last_login > 3600):
            if not self._http_login_once(): 
                self._fetch_public_nifty()
                return

        try:
            url = "https://api.shoonya.com/NorenWClientTP/GetQuotes"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0'
            }
            payload = {
                "uid": self.client_id,
                "exch": "NSE",
                "token": "26000" # Nifty 50 Index on NSE
            }
            jData = "jData=" + json.dumps(payload) + f"&jKey={self.token}"
            resp = requests.post(url, data=jData, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                rj = resp.json()
                if rj.get('stat') == 'Ok':
                    lp = float(rj.get('lp', 0))
                    if lp > 0:
                        shared_data.market_data["NIFTY"] = lp
                        logger.info(f"🔥 [SHOONYA LIVE] NIFTY SPOT: {lp}")
                        return
                else:
                    logger.warning(f"⚠️ Shoonya LTP Error: {rj.get('emsg')}")
            
            # If Shoonya specific quote fails, try public fallback
            self._fetch_public_nifty()
        except Exception as e:
            logger.error(f"❌ Shoonya Feed Critical Error: {e}")
            self._fetch_public_nifty()
        finally:
            shared_data.broker_connection_status["Shoonya"] = (shared_data.market_data.get("NIFTY", 0) > 0)

    def _fetch_public_nifty(self):
        """🌍 EMERGENCY FALLBACK: Fetch Nifty from Yahoo Finance mirror if Shoonya fails."""
        try:
            resp = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                lp = data['chart']['result'][0]['meta']['regularMarketPrice']
                shared_data.market_data["NIFTY"] = float(lp)
                logger.info(f"🌍 [PUBLIC FALLBACK] NIFTY SPOT: {lp}")
        except Exception as e:
            logger.error(f"⚠️ Public Fallback Failed: {e}")

    def start_feed(self):
        self.is_running = True
        logger.info("🚀 [GVN] Shoonya Feed Engine v3.0 Starting...")
        threading.Thread(target=self._run_polling, daemon=True).start()

    def _run_polling(self):
        while self.is_running:
            self.fetch_ltp_direct()
            time.sleep(3)

def start_shoonya_worker():
    from app import app, db, UserBrokerConfig
    with app.app_context():
        config = UserBrokerConfig.query.filter_by(user_id=1).first()
        if config and config.client_id:
            try:
                creds = config.get_credentials()
                worker = ShoonyaLiveFeed(
                    client_id=config.client_id,
                    password=creds.get('password'),
                    api_secret=creds.get('api_secret'),
                    totp_key=creds.get('totp_key'),
                    vendor_code=config.api_key # api_key stores vendor_code/access_token
                )
                shared_data.active_shoonya_worker = worker
                worker.start_feed()
            except Exception as e:
                logger.error(f"⚠️ Shoonya Feed Startup Error: {e}")

if __name__ == "__main__":
    start_shoonya_worker()
    while True: time.sleep(1)
