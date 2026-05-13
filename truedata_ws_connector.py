import os
import time
import logging
import threading
from dotenv import load_dotenv
from truedata import TD_live
from datetime import datetime as dt
import shared_data

# Load credentials
load_dotenv()

logger = logging.getLogger("TrueDataWebSocket")

class TrueDataWSConnector:
    """
    High-Speed WebSocket Connector using truedata TD_live.
    Provides real-time Option Chain, Greeks, and Tick data.
    """
    def __init__(self, username=None, password=None):
        # Using Trial credentials as requested by user
        self.username = "Trial245"
        self.password = "nelson245"
        self.td_obj = None
        self.is_running = False
        self.symbols = ["NIFTY", "BANKNIFTY", "SBIN", "CRUDEOIL"]
        self.chain_objects = {} 

    def start(self):
        try:
            logger.info(f"🚀 Connecting to TrueData WebSocket for {self.username}...")
            # Following sample code's live_port
            self.td_obj = TD_live(self.username, self.password, live_port=8086, log_level=logging.WARNING)
            
            self.td_obj.start_live_data(self.symbols)
            self._setup_callbacks()
            
            self.is_running = True
            logger.info("✅ TrueData WebSocket Connected!")
            
            threading.Thread(target=self._run_loop, daemon=True).start()
            self.initialize_default_chains()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to TrueData WS: {e}")
 
    def initialize_default_chains(self):
        """Starts option chains with dynamic expiry detection from REST API"""
        try:
            from shared_data import td_api
            
            # 1. Fetch Dynamic Expiries
            nifty_expiries = []
            crude_expiries = []
            if td_api:
                nifty_expiries = td_api.get_expiry_list("NIFTY")
                crude_expiries = td_api.get_expiry_list("CRUDEOIL")
            
            # 🔍 [GVN DEBUG] Log all available expiries
            logger.info(f"🔍 [EXPIRY SCAN] NIFTY Expiries: {nifty_expiries}")
            logger.info(f"🔍 [EXPIRY SCAN] CRUDEOIL Expiries: {crude_expiries}")

            # 🚀 GVN SPECIAL: Search for the best working expiry
            n_expiry = None
            for exp_str in ["21-05-2026", "14-05-2026", "19-05-2026"]:
                if nifty_expiries and exp_str in nifty_expiries:
                    n_expiry = dt.strptime(exp_str, "%d-%m-%Y")
                    break
            
            if not n_expiry:
                if nifty_expiries and len(nifty_expiries) > 0:
                    n_expiry = dt.strptime(nifty_expiries[0], "%d-%m-%Y")
                else:
                    n_expiry = dt(2026, 5, 21) # Safe default fallback

            c_expiry = dt.strptime(crude_expiries[0], "%d-%m-%Y") if (crude_expiries and isinstance(crude_expiries, list) and len(crude_expiries) > 0) else dt(2026, 5, 14)
            
            # 2. Start CRUDEOIL Chain
            logger.info(f"📈 Initializing CRUDEOIL Chain for {c_expiry.date()}")
            self.start_option_chain('CRUDEOIL', c_expiry)
            
            # 3. Start NIFTY Chain
            logger.info(f"📈 Initializing NIFTY Chain for {n_expiry.date()}")
            self.start_option_chain('NIFTY', n_expiry)
            
        except Exception as e:
            logger.error(f"Error in dynamic chain initialization: {e}")

    def _setup_callbacks(self):
        @self.td_obj.trade_callback
        def on_tick(tick_data):
            try:
                # Map "NIFTY 50" to "NIFTY" for system consistency
                symbol = tick_data.symbol
                if symbol == "NIFTY 50": symbol = "NIFTY"
                elif "-I" in symbol: symbol = symbol.replace("-I", "")
                
                # Correct attribute for TrueData tick is .ltp
                price = getattr(tick_data, 'ltp', None)
                if price:
                    shared_data.update_market_data(symbol, float(price))
            except Exception as e:
                pass 

        @self.td_obj.greek_callback
        def on_greek(greek_data):
            # Greeks are typically handled within the chain object, but can be logged here
            pass

    def start_option_chain(self, symbol, expiry_date):
        """Initializes a live option chain"""
        if self.td_obj:
            logger.info(f"📈 Initializing WebSocket Option Chain for {symbol} ({expiry_date.date()})")
            chain = self.td_obj.start_option_chain(symbol, expiry_date, chain_length=20, bid_ask=True, greek=True)
            self.chain_objects[symbol] = chain
            return chain
        return None

    def _run_loop(self):
        """Background loop to update shared_data.truedata_option_chains"""
        while self.is_running:
            try:
                for symbol, chain_obj in self.chain_objects.items():
                    df = chain_obj.get_option_chain()
                    if df is not None and not df.empty:
                        # Convert DataFrame to list of dicts for JSON serialization in Flask
                        chain_list = df.to_dict('records')
                        shared_data.truedata_option_chains[symbol] = chain_list
                
                # Update status
                shared_data.broker_connection_status["TrueDataWS"] = True
                
                time.sleep(1) # Refresh rate for option chain in memory
            except Exception as e:
                logger.error(f"Error in TrueData WS loop: {e}")
                time.sleep(5)

def start_truedata_ws_engine():
    connector = TrueDataWSConnector()
    connector.start()
    return connector

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    conn = start_truedata_ws_engine()
    while True:
        time.sleep(1)
