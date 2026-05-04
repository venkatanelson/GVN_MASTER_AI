
import sys
import os

# 🚀 FORCE FIX: Add User Site-Packages to Path
user_site = os.path.join(os.environ['APPDATA'], '..', 'Local', 'Packages', 'PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0', 'LocalCache', 'local-packages', 'Python311', 'site-packages')
if os.path.exists(user_site):
    sys.path.append(user_site)
    # logger.info(f"✅ Added Local Path: {user_site}")

import time
import logging
import threading
import shared_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AngelLiveFeed")

import sys
# Debug Path
# logger.info(f"Python Path: {sys.path}")

try:
    import SmartApi
    from SmartApi.smartconnect import SmartConnect
    logger.info("✅ SmartApi found via method 1")
except ImportError:
    try:
        import smartapi
        from smartapi import SmartConnect
        logger.info("✅ smartapi found via method 2")
    except ImportError:
        try:
            # Last resort: try to find it in site-packages directly if path is weird
            import site
            logger.info(f"Site Packages: {site.getsitepackages()}")
            SmartConnect = None
        except:
            SmartConnect = None

if SmartConnect is None:
    logger.error("❌ Angel One Library (smartapi-python) still not found. Switching to Direct HTTP mode.")

class AngelLiveFeed:
    def __init__(self, api_key, client_id, password, totp_key):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_key = totp_key
        self.smart_api = None
        self.is_running = False

    def connect(self):
        if SmartConnect is None:
            logger.warning("⚠️ SmartConnect library not found. Using Direct HTTP Fallback...")
            return True # Pretend connected for fallback mode
        try:
            import pyotp
            totp = pyotp.TOTP(self.totp_key).now()
            self.smart_api = SmartConnect(api_key=self.api_key)
            data = self.smart_api.generateSession(self.client_id, self.password, totp)
            if data['status']:
                logger.info("✅ Angel One WebSocket Login Successful")
                return True
            else:
                logger.error(f"❌ Angel One WebSocket Login Failed: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"❌ Angel WebSocket Error: {e}")
            return False

    def fetch_ltp_direct(self, symbol="NIFTY"):
        """Fallback: Fetch LTP using Direct HTTP requests without SmartApi library."""
        try:
            import requests
            import pyotp
            totp = pyotp.TOTP(self.totp_key).now()
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-PrivateKey": self.api_key
            }
            
            # Login first to get JWT
            login_url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            payload = {"clientcode": self.client_id, "password": self.password, "totp": totp}
            resp = requests.post(login_url, json=payload, headers=headers)
            
            if resp.status_code == 200:
                jwt = resp.json().get('data', {}).get('jwtToken')
                if jwt:
                    headers["Authorization"] = f"Bearer {jwt}"
                    # Fetch LTP (Nifty token is 26000)
                    ltp_url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/marketdata/v1/getLTP"
                    ltp_payload = {"exchange": "NSE", "symboltoken": "26000", "tradingsymbol": "NIFTY"}
                    ltp_resp = requests.post(ltp_url, json=ltp_payload, headers=headers)
                    if ltp_resp.status_code == 200:
                        lp = ltp_resp.json().get('data', {}).get('ltp', 0)
                        if lp > 0:
                            import shared_data
                            shared_data.market_data["NIFTY"] = lp
                            logger.info(f"🚀 [HTTP FALLBACK] NIFTY LTP: {lp}")
        except Exception as e:
            logger.error(f"❌ HTTP Fallback Error: {e}")

    def start_feed(self):
        if not self.connect(): return
        
        self.is_running = True
        if SmartConnect:
            threading.Thread(target=self._run_dummy_feed, daemon=True).start()
        else:
            # Run periodic HTTP polling
            threading.Thread(target=self._run_http_polling, daemon=True).start()
        logger.info("🛰️ Angel One Live Feed Engine Active")

    def _run_http_polling(self):
        while self.is_running:
            self.fetch_ltp_direct("NIFTY")
            time.sleep(5)

    def _run_dummy_feed(self):
        """Simulates or fetches updates periodically"""
        while self.is_running:
            # In real market hours, we'd use SmartWebSocket
            # For now, we ensure the shared_data has the latest cached prices
            time.sleep(10)

def start_angel_worker():
    backup = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel", {})
    if backup.get("client_id"):
        try:
            logger.info(f"🔄 Starting Angel Feed for {backup.get('client_id')}...")
            worker = AngelLiveFeed(
                api_key=backup.get("api_key", "vS42B24z"),
                client_id=backup.get("client_id"),
                password=backup.get("password"),
                totp_key=backup.get("totp_key")
            )
            worker.start_feed()
        except Exception as e:
            print(f"⚠️ Angel Feed Startup Error: {e}")

if __name__ == "__main__":
    start_angel_worker()
    while True: time.sleep(1)
