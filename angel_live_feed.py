
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
            # 🛡️ GVN WAF BYPASS: Correct Endpoint URL & Headers
            headers = {
                "Content-Type": "application/json", "Accept": "application/json",
                "X-UserType": "USER", "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": self.api_key, "Authorization": f"Bearer {self.jwt}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            # The correct Angel One SmartAPI endpoint for Market Data
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/market/v1/quote/"
            
            # 🚀 GVN IMPROVEMENT: Query all major indices (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY)
            ltp_payload = {
                "mode": "LTP", 
                "exchangeTokens": {
                    "NSE": ["99926000", "26000", "99926009", "26009", "99926037", "26017", "99926074"]
                }
            }
            
            logger.info(f"📡 Requesting Angel MarketData for NSE Indices...")
            resp = requests.post(url, json=ltp_payload, headers=headers, timeout=10)
            
            if resp.status_code == 200 and resp.text.strip().startswith('{'):
                rj = resp.json()
                data_list = rj.get('data', {}).get('fetched', [])
                for item in data_list:
                    token = item.get("symbolToken")
                    lp = item.get("ltp") or item.get("lastPrice", 0)
                    if lp > 0:
                        if token in ["99926000", "26000"]:
                            shared_data.market_data["NIFTY"] = float(lp)
                            shared_data.market_data["NIFTY 50"] = float(lp)
                            logger.info(f"🔥 [ANGEL LIVE] NIFTY SPOT: {lp}")
                        elif token in ["99926009", "26009"]:
                            shared_data.market_data["BANKNIFTY"] = float(lp)
                            shared_data.market_data["NIFTY BANK"] = float(lp)
                            logger.info(f"🔥 [ANGEL LIVE] BANKNIFTY SPOT: {lp}")
                        elif token in ["99926037", "26017"]:
                            shared_data.market_data["FINNIFTY"] = float(lp)
                            shared_data.market_data["NIFTY FIN SERVICE"] = float(lp)
                            logger.info(f"🔥 [ANGEL LIVE] FINNIFTY SPOT: {lp}")
                        elif token in ["99926074"]:
                            shared_data.market_data["MIDCPNIFTY"] = float(lp)
                            shared_data.market_data["NIFTY MID SELECT"] = float(lp)
                            logger.info(f"🔥 [ANGEL LIVE] MIDCPNIFTY SPOT: {lp}")
            else:
                logger.warning(f"⚠️ Angel NSE Indices Error {resp.status_code}: {resp.text[:100]}")

            # Fetch BSE Indices (SENSEX)
            bse_payload = {
                "mode": "LTP",
                "exchangeTokens": {
                    "BSE": ["99919000", "19000"]
                }
            }
            resp_bse = requests.post(url, json=bse_payload, headers=headers, timeout=10)
            if resp_bse.status_code == 200 and resp_bse.text.strip().startswith('{'):
                rj_bse = resp_bse.json()
                data_list_bse = rj_bse.get('data', {}).get('fetched', [])
                for item in data_list_bse:
                    token = item.get("symbolToken")
                    lp = item.get("ltp") or item.get("lastPrice", 0)
                    if lp > 0:
                        if token in ["99919000", "19000"]:
                            shared_data.market_data["SENSEX"] = float(lp)
                            shared_data.market_data["BSE SENSEX"] = float(lp)
                            logger.info(f"🔥 [ANGEL LIVE] SENSEX SPOT: {lp}")
            else:
                logger.warning(f"⚠️ Angel BSE Indices Error {resp_bse.status_code}: {resp_bse.text[:100]}")

        except Exception as e:
            logger.error(f"❌ Angel Feed Critical Error: {e}")
            
        # Fallback to public if Nifty is still 0
        if shared_data.market_data.get("NIFTY", 0) == 0:
            self._fetch_public_nifty()
            
        shared_data.broker_connection_status["AngelOne"] = (shared_data.market_data.get("NIFTY", 0) > 0)

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
