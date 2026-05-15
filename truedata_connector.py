import os
import time
import logging
from dotenv import load_dotenv
load_dotenv()
import shared_data
from truedata_rest_api import TrueDataRestAPI

logger = logging.getLogger("TrueDataConnector")

class TrueDataRestConnector:
    """
    Fallback Connector using REST API when WebSocket credentials are missing.
    Uses the token found in the documentation/Postman collection.
    """
    def __init__(self, token=None):
        self.api = TrueDataRestAPI(token)
        self.symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]
        self.is_running = False

    def start(self):
        self.is_running = True
        import threading
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info("🚀 TrueData REST Live Feed Started")

    def _run_loop(self):
        while self.is_running:
            try:
                for sym in self.symbols:
                    # Fetching LTP for spot
                    res = self.api.get_ltp_spot(sym)
                    if res and isinstance(res, dict):
                        ltp = res.get('lastTradedPrice') or res.get('ltp')
                        if ltp:
                            shared_data.update_market_data(sym.upper(), float(ltp))
                            # 🚀 GVN SYNC: Force uppercase and update global pulse
                            shared_data.market_data[sym.upper()] = float(ltp)
                
                # High frequency polling (100ms)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in TrueData REST loop: {e}")
                time.sleep(1)

def start_truedata_engine(username=None, password=None, token=None):
    """
    Starts TrueData Engine. 
    Loads credentials from .env if not provided.
    """
    username = username or os.getenv("TRUEDATA_USERNAME")
    password = password or os.getenv("TRUEDATA_PASSWORD")
    
    logger.info("Using TrueData High-Speed REST Engine (Auto-Login)")
    connector = TrueDataRestConnector(token)
    # Inject credentials into the REST API object
    connector.api.username = username
    connector.api.password = password
    connector.api.login() # Attempt fresh login
    
    connector.start()
    return connector
