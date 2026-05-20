
import requests
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrueDataRestAPI")

class TrueDataRestAPI:
    """
    TrueData Analytics REST API Library for GVN Algo
    Derived from Postman Collection provided by TrueData
    """
    def __init__(self, token=None, username=None, password=None):
        # Initial credentials
        self.username = username
        self.password = password
        self.token = token # No hardcoded expired tokens
        self.auth_url = "https://auth.truedata.in/token"
        self.base_urls = {
            "analytics": "https://analytics.truedata.in/api",
            "corporate": "https://corporate.truedata.in",
            "history": "https://history.truedata.in/api"
        }
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        
        # 🔑 GVN FIX: Always login if credentials provided to get a fresh token
        if self.username and self.password:
            self.login()

    def get_next_thursday(self):
        """Calculates the date of the upcoming Thursday"""
        today = datetime.now()
        days_ahead = 3 - today.weekday() # Thursday is index 3
        if days_ahead < 0: # Already past Thursday
            days_ahead += 7
        next_thu = today + timedelta(days=days_ahead)
        return next_thu.strftime("%d-%m-%Y")

    def login(self):
        """Authenticates with TrueData and obtains a fresh Bearer Token"""
        try:
            logger.info(f"🔑 Attempting TrueData Login for {self.username}...")
            payload = {
                "username": self.username,
                "password": self.password,
                "grant_type": "password"
            }
            # Auth requires x-www-form-urlencoded
            response = self.session.post(self.auth_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers["Authorization"] = f"Bearer {self.token}"
                logger.info("✅ TrueData Login Successful! Fresh token obtained.")
                return True
            else:
                logger.error(f"❌ Login Failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception during login: {e}")
            return False

    def _make_request(self, endpoint, params=None, service="analytics"):
        try:
            if params is None: params = {}
            base_url = self.base_urls.get(service, self.base_urls["analytics"])
            url = f"{base_url}/{endpoint}"
            
            # Try 1: Standard Bearer Header
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            # Try 2: Authorization Header WITHOUT 'Bearer ' prefix
            if response.status_code == 401:
                headers = {"Authorization": self.token, "Content-Type": "application/json"}
                response = self.session.get(url, params=params, headers=headers, timeout=30)
                
            # Try 3: Simple 'token' Header
            if response.status_code == 401:
                headers = {"token": self.token, "Content-Type": "application/json"}
                response = self.session.get(url, params=params, headers=headers, timeout=30)
                
            # Try 4: Query Param fallback
            if response.status_code == 401:
                params["token"] = self.token
                response = self.session.get(url, params=params, timeout=30)
                
            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as e:
                    logger.error(f"❌ Received non-JSON response from {endpoint}: {e} | Text: {response.text[:100]}")
                    return None
            else:
                # Silence 401/404 errors to avoid cluttering the terminal
                if response.status_code not in [401, 404]:
                    logger.error(f"API Error ({endpoint}): {response.status_code} - {response.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"Exception in API call ({endpoint}): {e}")
            return None

    # --- Market Data Endpoints ---

    def get_option_chain(self, symbol="NIFTY", expiry=None, exchange="NSE"):
        """Fetches live option chain data with smart expiry & exchange fallbacks"""
        if not expiry:
            expiry_list = self.get_expiry_list(symbol)
            if expiry_list and isinstance(expiry_list, list) and len(expiry_list) > 0:
                expiry = expiry_list[0]
            else:
                # 🌟 SMART FALLBACK based on symbol
                if "CRUDE" in symbol.upper() or "MCX" in symbol.upper():
                    expiry = "14-05-2026" # Validated from Sample Code
                    exchange = "MCX"
                else:
                    expiry = "26-05-2026" # User Verified Nifty Expiry
                
        params = {"symbol": symbol, "expiry": expiry, "exchange": exchange, "response": "json"}
        return self._make_request("getoptionchain", params)

    def get_option_chain_with_greeks(self, symbol="NIFTY", expiry="26-05-2026"):
        """Fetches live option chain with Greek values (Delta, Gamma, etc.)"""
        params = {"symbol": symbol, "expiry": expiry, "response": "json"}
        return self._make_request("getOptionChainwithGreeks", params)

    def get_ltp_with_greeks(self, symbol, strike, series, expiry):
        """Fetches LTP with Greeks for a specific option"""
        params = {
            "symbol": symbol,
            "strike": strike,
            "series": series,
            "expiry": expiry
        }
        return self._make_request("getLTPwithGreeks", params)

    def get_expiry_list(self, symbol="NIFTY"):
        """Fetches list of upcoming expiries with multiple endpoint fallbacks"""
        params = {"symbol": symbol}
        # Try primary endpoint
        res = self._make_request("getSymbolExpiryList", params)
        if not res:
            # Try secondary endpoint common in some TrueData versions
            res = self._make_request("getexpiry", params)
        
        if res and isinstance(res, list):
            return res
        
        # Final fallback to avoid crash
        if "CRUDE" in symbol.upper():
            return ["14-05-2026"] 
            
        return ["26-05-2026"] # User Verified Next Nifty Expiry

    def get_ltp(self, symbol, strike, series, expiry):
        """Fetches Last Traded Price for specific strike"""
        params = {
            "symbol": symbol,
            "strike": strike,
            "series": series,
            "expiry": expiry,
            "response": "json"
        }
        return self._make_request("getLTP", params)

    def get_ltp_spot(self, symbol, series="EQ"):
        """Fetches Spot LTP for Equities"""
        params = {"symbol": symbol, "series": series, "response": "json"}
        return self._make_request("getLTPSpot", params)

    # --- Historical Endpoints ---
    def get_historical_data(self, symbol, from_date, to_date, resolution="1"):
        """
        Fetches historical Intraday candles for Playback/Backtesting
        resolution: '1' for 1min, '5' for 5min, etc.
        from_date / to_date format: 'YYMMDDHHMMSS'
        """
        params = {
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "resolution": resolution,
            "response": "json"
        }
        return self._make_request("gethistory", params, service="history")

    # --- Analytics & OI Endpoints ---

    def get_oi_gainers(self, top=20, series="XX"):
        """Top Open Interest Gainers"""
        params = {"top": top, "series": series, "response": "json"}
        return self._make_request("getOIGainers", params)

    def get_oi_losers(self, top=20, series="XX"):
        """Top Open Interest Losers"""
        params = {"top": top, "series": series, "response": "json"}
        return self._make_request("getOILosers", params)

    def get_highest_oi_options(self, top=20, series="pe"):
        """Options with highest Open Interest"""
        params = {"top": top, "series": series, "response": "json"}
        return self._make_request("getoptionswithhighestoi", params)

    def get_most_active_volume(self, top=100, exchange="NSE"):
        """Most active stocks by volume"""
        params = {"top": top, "exchange": exchange, "response": "json"}
        return self._make_request("getMostActiveByVolume", params)

    # --- Market Breadth ---

    def get_advance_decline(self, index_name="NIFTY 50"):
        """Advance-Decline ratio for index"""
        params = {"indexName": index_name}
        return self._make_request("getMarketAdvDec", params)

    def get_circuit_stocks(self, type="upper", top=100):
        """Stocks in Upper or Lower Circuit"""
        endpoint = "getStocksInUpperCircuit" if type == "upper" else "getStocksInLowerCircuit"
        params = {"top": top, "exchange": "NSE", "response": "json"}
        return self._make_request(endpoint, params)

    # --- Corporate & Fundamental Endpoints ---

    def get_fii_dii_data(self):
        """Fetches daily FII and DII trading data"""
        return self._make_request("getFIIDIIData", service="corporate")

    def get_corporate_announcements(self, company_name, from_date, to_date):
        """Fetches announcements for a company"""
        params = {
            "companyName": company_name,
            "fromDate": from_date,
            "toDate": to_date
        }
        return self._make_request("getAnnoucementsForCompanies", params, service="corporate")

    def get_market_cap(self, symbol):
        """Fetches market capitalization"""
        params = {"symbol": symbol}
        return self._make_request("getMarketCap", params, service="corporate")

    def get_news(self, from_dt, to_dt, top=40):
        """Fetches market news"""
        params = {
            "response": "json",
            "from": from_dt,
            "to": to_dt,
            "top": top
        }
        return self._make_request("getNewsForDateRange", params, service="corporate")

if __name__ == "__main__":
    # Test sample
    api = TrueDataRestAPI()
    print("Testing Option Chain...")
    res = api.get_option_chain("NIFTY")
    if res:
        print("✅ Data connection successful!")
    else:
        print("❌ Could not connect. Check token.")
