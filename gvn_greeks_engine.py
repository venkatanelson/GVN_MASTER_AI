"""
GVN Greeks Engine: Real-time Delta, Gamma, Theta, Vega Calculator
Monitors 28 strikes (14 CE, 14 PE) with precise Greek calculations
"""

import math
from datetime import datetime, timedelta
import requests
import json
from scipy.stats import norm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GreeksEngine")

# ───────────────────────────────────────────────────────────────
# BLACK-SCHOLES GREEKS CALCULATOR
# ───────────────────────────────────────────────────────────────

class BlackScholesGreeks:
    """Calculate Greeks using Black-Scholes model"""
    
    @staticmethod
    def d1(S, K, T, r, sigma):
        """Calculate d1"""
        if T <= 0 or sigma <= 0:
            return 0
        return (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma * math.sqrt(T))
    
    @staticmethod
    def d2(S, K, T, r, sigma):
        """Calculate d2"""
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        if T <= 0 or sigma <= 0:
            return 0
        return d1 - sigma * math.sqrt(T)
    
    @staticmethod
    def delta(S, K, T, r, sigma, option_type='CE'):
        """Calculate Delta (rate of change of option price w.r.t. stock price)"""
        if T <= 0:
            return 1.0 if option_type == 'CE' and S > K else 0.0
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        if option_type == 'CE':
            return norm.cdf(d1)
        else:  # PE
            return norm.cdf(d1) - 1
    
    @staticmethod
    def gamma(S, K, T, r, sigma):
        """Calculate Gamma (rate of change of Delta)"""
        if T <= 0 or sigma <= 0:
            return 0
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * math.sqrt(T))
    
    @staticmethod
    def theta(S, K, T, r, sigma, option_type='CE'):
        """Calculate Theta (time decay per day)"""
        if T <= 0 or sigma <= 0:
            return 0
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        d2 = BlackScholesGreeks.d2(S, K, T, r, sigma)
        
        term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
        
        if option_type == 'CE':
            term2 = -r * K * math.exp(-r*T) * norm.cdf(d2)
            theta = (term1 + term2) / 365
        else:  # PE
            term2 = r * K * math.exp(-r*T) * norm.cdf(-d2)
            theta = (term1 + term2) / 365
        
        return theta
    
    @staticmethod
    def vega(S, K, T, r, sigma):
        """Calculate Vega (sensitivity to volatility change)"""
        if T <= 0 or sigma <= 0:
            return 0
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        return S * norm.pdf(d1) * math.sqrt(T) / 100  # Per 1% change in volatility
    
    @staticmethod
    def call_price(S, K, T, r, sigma):
        """Calculate Call option price"""
        if T <= 0:
            return max(S - K, 0)
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        d2 = BlackScholesGreeks.d2(S, K, T, r, sigma)
        return S * norm.cdf(d1) - K * math.exp(-r*T) * norm.cdf(d2)
    
    @staticmethod
    def put_price(S, K, T, r, sigma):
        """Calculate Put option price"""
        if T <= 0:
            return max(K - S, 0)
        d1 = BlackScholesGreeks.d1(S, K, T, r, sigma)
        d2 = BlackScholesGreeks.d2(S, K, T, r, sigma)
        return K * math.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)


# ───────────────────────────────────────────────────────────────
# OPTION CHAIN HARVESTER (Shoonya/Dhan)
# ───────────────────────────────────────────────────────────────

class OptionChainHarvester:
    """Fetch option chain data from brokers"""
    
    def __init__(self, broker_config):
        self.broker = broker_config.get("broker_name", "Shoonya").lower()
        self.config = broker_config
        self.cache = {}
        self.last_update = {}
    
    def fetch_shoonya_option_chain(self, symbol, expiry_date):
        """Fetch option chain from Shoonya API"""
        try:
            # Shoonya direct HTTP endpoint for option chain
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GVN-Master-Algo"
            }
            
            params = {
                "mode": "FULL",
                "exchangetokens": symbol,
                "expirydate": expiry_date,
                "strikeoffset": 100,  # Get strikes around current price
                "cnt": 50
            }
            
            # This would connect to Shoonya's actual endpoint
            # For now, return mock data structure
            logger.info(f"📊 Fetching option chain for {symbol} from Shoonya")
            return self._create_mock_chain(symbol)
            
        except Exception as e:
            logger.error(f"Shoonya chain fetch failed: {e}")
            return None
    
    def fetch_dhan_option_chain(self, symbol):
        """Fetch option chain from Dhan API"""
        try:
            headers = {
                "access-token": self.config.get("access_token"),
                "client-id": self.config.get("client_id"),
                "Content-Type": "application/json"
            }
            
            # Dhan option chain endpoint
            # Example: /optionchain/{exchangeTokens}
            logger.info(f"📊 Fetching option chain for {symbol} from Dhan")
            return self._create_mock_chain(symbol)
            
        except Exception as e:
            logger.error(f"Dhan chain fetch failed: {e}")
            return None
    
    def _create_mock_chain(self, symbol):
        """Create mock option chain data for testing"""
        # In production, this would be replaced with actual API calls
        chain = {
            "symbol": symbol,
            "spot_price": 25000 if symbol == "NIFTY" else 50000,
            "expiry": (datetime.now() + timedelta(days=1)).strftime("%d-%b-%Y"),
            "calls": [],
            "puts": []
        }
        
        spot = chain["spot_price"]
        base_strike = (spot // 100) * 100  # Round to nearest 100
        
        # Generate 14 strikes each side (28 total)
        for i in range(-7, 8):
            strike = base_strike + (i * 100)
            
            # Call option
            chain["calls"].append({
                "strike": strike,
                "bid": max(spot - strike, 0),
                "ask": max(spot - strike, 0) + 5,
                "volume": 1000 * (8 - abs(i)),
                "oi": 50000 * (8 - abs(i))
            })
            
            # Put option
            chain["puts"].append({
                "strike": strike,
                "bid": max(strike - spot, 0),
                "ask": max(strike - spot, 0) + 5,
                "volume": 1000 * (8 - abs(i)),
                "oi": 50000 * (8 - abs(i))
            })
        
        return chain


# ───────────────────────────────────────────────────────────────
# ALPHA GRID MONITOR (28 Strikes with Greeks)
# ───────────────────────────────────────────────────────────────

class AlphaGridMonitor:
    """Monitor 28 strikes with real-time Greeks calculation"""
    
    def __init__(self, broker_config):
        self.harvester = OptionChainHarvester(broker_config)
        self.greeks_calc = BlackScholesGreeks()
        self.alpha_grid = []
        self.risk_free_rate = 0.06  # 6% annual
        self.volatility = 0.25  # 25% implied vol (market dependent)
    
    def calculate_strike_greeks(self, spot_price, strike, option_type, days_to_expiry):
        """Calculate Greeks for a single strike"""
        T = days_to_expiry / 365.0
        
        greeks = {
            "strike": strike,
            "type": option_type,
            "delta": round(self.greeks_calc.delta(spot_price, strike, T, self.risk_free_rate, self.volatility, option_type), 4),
            "gamma": round(self.greeks_calc.gamma(spot_price, strike, T, self.risk_free_rate, self.volatility), 6),
            "theta": round(self.greeks_calc.theta(spot_price, strike, T, self.risk_free_rate, self.volatility, option_type), 4),
            "vega": round(self.greeks_calc.vega(spot_price, strike, T, self.risk_free_rate, self.volatility), 4),
        }
        
        if option_type == 'CE':
            greeks["price"] = round(self.greeks_calc.call_price(spot_price, strike, T, self.risk_free_rate, self.volatility), 2)
        else:
            greeks["price"] = round(self.greeks_calc.put_price(spot_price, strike, T, self.risk_free_rate, self.volatility), 2)
        
        return greeks
    
    def build_alpha_grid(self, symbol, spot_price, chain_data):
        """Build complete alpha grid from option chain"""
        if not chain_data:
            logger.warning(f"No chain data for {symbol}")
            return []
        
        days_to_expiry = 1  # Assuming next day expiry
        grid = {
            "symbol": symbol,
            "spot": spot_price,
            "timestamp": datetime.now().isoformat(),
            "calls": [],
            "puts": []
        }
        
        # Process calls
        for call in chain_data.get("calls", [])[:14]:
            greeks = self.calculate_strike_greeks(spot_price, call["strike"], "CE", days_to_expiry)
            greeks.update({
                "bid": call.get("bid", 0),
                "ask": call.get("ask", 0),
                "volume": call.get("volume", 0),
                "oi": call.get("oi", 0)
            })
            grid["calls"].append(greeks)
        
        # Process puts
        for put in chain_data.get("puts", [])[:14]:
            greeks = self.calculate_strike_greeks(spot_price, put["strike"], "PE", days_to_expiry)
            greeks.update({
                "bid": put.get("bid", 0),
                "ask": put.get("ask", 0),
                "volume": put.get("volume", 0),
                "oi": put.get("oi", 0)
            })
            grid["puts"].append(greeks)
        
        self.alpha_grid = grid
        logger.info(f"✅ Alpha Grid built: {len(grid['calls'])} CE + {len(grid['puts'])} PE strikes")
        return grid


# ───────────────────────────────────────────────────────────────
# STRIKE SELECTOR: 0.60-0.69 Delta Filter
# ───────────────────────────────────────────────────────────────

class StrikeSelector:
    """Select best strikes based on Delta range (0.60-0.69)"""
    
    @staticmethod
    def filter_by_delta(alpha_grid, delta_min=0.60, delta_max=0.69):
        """Filter strikes within delta range"""
        selected = {
            "calls": [],
            "puts": []
        }
        
        # Filter calls
        for call in alpha_grid.get("calls", []):
            delta = abs(call.get("delta", 0))
            if delta_min <= delta <= delta_max:
                selected["calls"].append(call)
        
        # Filter puts  
        for put in alpha_grid.get("puts", []):
            delta = abs(put.get("delta", 0))
            if delta_min <= delta <= delta_max:
                selected["puts"].append(put)
        
        logger.info(f"📍 Selected {len(selected['calls'])} CE + {len(selected['puts'])} PE strikes in 0.60-0.69 Delta range")
        return selected
    
    @staticmethod
    def rank_by_gamma(strikes, top_n=3):
        """Rank strikes by Gamma (momentum indicator)"""
        ranked = sorted(strikes, key=lambda x: x.get("gamma", 0), reverse=True)[:top_n]
        logger.info(f"🎯 Top {top_n} strikes by Gamma momentum")
        return ranked


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Mock config
    config = {
        "broker_name": "Shoonya",
        "access_token": "test_token",
        "client_id": "test_client"
    }
    
    # Initialize monitors
    monitor = AlphaGridMonitor(config)
    selector = StrikeSelector()
    
    # Simulate option chain
    chain = monitor.harvester.fetch_shoonya_option_chain("NIFTY", "29-Apr-2026")
    
    # Build alpha grid
    grid = monitor.build_alpha_grid("NIFTY", 25000, chain)
    
    # Select best strikes
    selected = selector.filter_by_delta(grid, 0.60, 0.69)
    best_calls = selector.rank_by_gamma(selected["calls"], 3)
    best_puts = selector.rank_by_gamma(selected["puts"], 3)
    
    print(f"\n✅ Greeks Engine Initialized")
    print(f"   CE Strikes in Delta Range: {len(selected['calls'])}")
    print(f"   PE Strikes in Delta Range: {len(selected['puts'])}")
