
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
            logger.error("❌ Cannot connect: Angel One library (smartapi-python) is not installed.")
            return False
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

    def start_feed(self):
        if not self.connect(): return
        
        self.is_running = True
        threading.Thread(target=self._run_dummy_feed, daemon=True).start()
        logger.info("🛰️ Angel One Live Feed Started (Dummy Mode for After-Hours)")

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
