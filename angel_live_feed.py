
import sys
import os
import time
import logging
import threading
import requests
import pyotp

# 🚀 FORCE FIX: Add User Site-Packages to Path
user_site = os.path.join(os.environ['APPDATA'], '..', 'Local', 'Packages', 'PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0', 'LocalCache', 'local-packages', 'Python311', 'site-packages')
if os.path.exists(user_site):
    sys.path.append(user_site)

import shared_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AngelLiveFeed")

class AngelLiveFeed:
    def __init__(self, api_key, client_id, password, totp_key):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_key = totp_key
        self.is_running = False
        self.jwt = None 
        self.last_login = 0

    def _http_login_once(self):
        try:
            totp = pyotp.TOTP(self.totp_key).now()
            headers = {
                "Content-Type": "application/json", "Accept": "application/json",
                "X-UserType": "USER", "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00", "X-PrivateKey": self.api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            payload = {"clientcode": self.client_id, "password": self.password, "totp": totp}
            resp = requests.post("https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword", json=payload, headers=headers)
            if resp.status_code == 200:
                rj = resp.json()
                if rj.get('status'):
                    self.jwt = rj.get('data', {}).get('jwtToken')
                    self.last_login = time.time()
                    logger.info("✅ Angel Session Established")
                    return True
            logger.error(f"❌ Login Failed: {resp.text[:100]}")
        except Exception as e:
            logger.error(f"❌ Login Error: {e}")
        return False

    def fetch_ltp_direct(self):
        if not self.jwt or (time.time() - self.last_login > 3600):
            if not self._http_login_once(): 
                self._fetch_public_nifty() # 🌟 Fallback to public data if login fails
                return

        try:
            headers = {
                "Content-Type": "application/json", "Accept": "application/json",
                "X-UserType": "USER", "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": self.api_key, "Authorization": f"Bearer {self.jwt}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            # Try newer MarketData API
            ltp_payload = {"mode": "LTP", "exchangeTokens": {"NSE": ["26000"]}}
            resp = requests.post("https://apiconnect.angelbroking.com/rest/auth/angelbroking/marketdata/v1/marketData", json=ltp_payload, headers=headers)
            
            if resp.status_code == 200:
                rj = resp.json()
                data_list = rj.get('data', {}).get('fetched', [])
                if data_list:
                    lp = data_list[0].get('ltp', 0)
                    if lp > 0:
                        shared_data.market_data["NIFTY"] = float(lp)
                        print(f"🔥 [GVN LIVE] NIFTY SPOT: {lp}")
                        return
            
            # If Angel fails, try public fallback
            self._fetch_public_nifty()
        except Exception as e:
            self._fetch_public_nifty()

    def _fetch_public_nifty(self):
        """🌟 EMERGENCY FALLBACK: Fetch Nifty from public sources if broker fails."""
        try:
            # Try a public financial data mirror
            resp = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                lp = data['chart']['result'][0]['meta']['regularMarketPrice']
                shared_data.market_data["NIFTY"] = float(lp)
                print(f"🌍 [PUBLIC FALLBACK] NIFTY SPOT: {lp}")
        except:
            pass

    def start_feed(self):
        self.is_running = True
        print("🚀 [GVN] Angel Feed Engine v3.0 (Triple-Fallback) Starting...")
        threading.Thread(target=self._run_polling, daemon=True).start()

    def _run_polling(self):
        while self.is_running:
            self.fetch_ltp_direct()
            time.sleep(3)

def start_angel_worker():
    backup = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel", {})
    if backup.get("client_id"):
        try:
            worker = AngelLiveFeed(
                api_key=backup.get("api_key"),
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
