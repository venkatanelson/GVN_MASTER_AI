import logging
import datetime
from collections import deque
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_WIND_ENGINE")

class GVNAiWindEngine:
    """
    GVN Institutional Option Chain Wind Reading System (MARKET DNA)
    Uses 5 Main Forces: OI, COI (Change in OI), Delta, Gamma, Theta
    """
    
    def __init__(self):
        self.vacuum_zones = []
        self.history = deque(maxlen=60)
        
    def calculate_wind_direction(self, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta):
        """
        Calculates Institutional Market Direction based on the 5 Main Forces.
        """
        try:
            # Prevent zero division errors
            total_vol = (ce_vol + pe_vol) if (ce_vol + pe_vol) > 0 else 1
            min_oi = min(ce_oi, pe_oi) if min(ce_oi, pe_oi) > 0 else 1
            
            # --- WIND POWER FORMULA COMPONENTS ---
            delta_strength = max(0.1, abs(delta))
            gamma_strength = max(0.1, gamma * 100) # Scaling gamma for mathematical logic
            volume_strength = max(0.1, abs(ce_vol - pe_vol) / total_vol)
            oi_strength = max(0.1, abs(pe_oi - ce_oi) / min_oi)
            theta_decay = max(0.1, abs(theta))
            
            # 🚀 MASTER WIND STRENGTH FORMULA
            wind_power = (delta_strength * gamma_strength * volume_strength * oi_strength) / theta_decay
            
            wind_state = "🟡 TRAP / SIDEWAYS"
            
            # --- THE 5 INSTITUTIONAL WIND STATES ---
            
            # 1. SHORT COVERING (Price ↑ + CE OI ↓)
            if ltp > vwap and ce_coi < 0 and delta > 0:
                wind_state = "🚀 SHORT COVERING (Fast Upside)"
                wind_power *= 1.5 # Boost power because shorts are trapped
                
            # 2. LONG UNWINDING (Price ↓ + PE OI ↓)
            elif ltp < vwap and pe_coi < 0 and delta < 0:
                wind_state = "🩸 LONG UNWINDING (Fast Fall)"
                wind_power *= 1.5 # Boost power because longs are trapped
                
            # 3. BULLISH WIND (UP WIND)
            elif ltp > vwap and pe_coi > ce_coi and delta > 0.2 and gamma > 0.005:
                wind_state = "🟢 UP WIND (Bullish - PUT Writing)"
                
            # 4. BEARISH WIND (DOWN WIND)
            elif ltp < vwap and ce_coi > pe_coi and delta < -0.2 and gamma > 0.005:
                wind_state = "🔴 DOWN WIND (Bearish - CALL Writing)"
                
            # 5. SIDEWAYS MARKET (Premium Eating)
            elif abs(ce_oi - pe_oi) < (min_oi * 0.15) and abs(delta) < 0.2 and gamma < 0.005:
                wind_state = "⚫ PREMIUM EATING (Sideways Market)"
                wind_power = min(wind_power, 0.7) # Force low power
            
            # --- MARKET STATES BASED ON WIND POWER ---
            if wind_power > 2.0:
                trend_type = "🔥 Strong Trend (Gamma Explosion Possible)"
            elif 1.2 <= wind_power <= 2.0:
                trend_type = "📈 Tradable Trend (Smooth Continuation)"
            elif 0.8 <= wind_power < 1.2:
                trend_type = "⚖️ Sideways (Wait for Breakout)"
            else:
                trend_type = "🪤 Trap Zone (High Danger for Option Buyers)"
                
            return {
                "wind_state": wind_state,
                "wind_power": round(wind_power, 2),
                "trend_type": trend_type,
                "metrics": {
                    "delta_pressure": round(delta_strength, 2),
                    "gamma_acceleration": round(gamma_strength, 2),
                    "theta_decay_rate": round(theta_decay, 2)
                }
            }
        except Exception as e:
            logger.error(f"Error in wind calculation: {e}")
            return {"wind_state": "ERROR", "wind_power": 0, "trend_type": "UNKNOWN"}

    def detect_liquidity_vacuum(self, ce_oi, pe_oi, previous_ce_oi, previous_pe_oi):
        """
        LIQUIDITY VACUUM DETECTOR
        Most dangerous move: Happens when one side OI suddenly disappears
        """
        try:
            ce_drop = previous_ce_oi - ce_oi
            pe_drop = previous_pe_oi - pe_oi
            
            # If 20% of OI vanishes suddenly -> VACUUM CREATED
            if previous_ce_oi > 0 and (ce_drop / previous_ce_oi) > 0.20:
                return "🚨 CALL LIQUIDITY VACUUM (No Resistance - Market Flies UP)"
                
            if previous_pe_oi > 0 and (pe_drop / previous_pe_oi) > 0.20:
                return "🚨 PUT LIQUIDITY VACUUM (No Support - Market Crashes DOWN)"
                
            return "Stable Liquidity"
        except Exception:
            return "Stable Liquidity"

    def get_market_dna(self, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta):
        """
        Returns full Market DNA Report (Smart Money Tracker)
        """
        wind_data = self.calculate_wind_direction(ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta)
        
        # Smart Money Tracker
        smart_money = "WAITING"
        if "UP WIND" in wind_data["wind_state"] or "SHORT COVERING" in wind_data["wind_state"]:
            smart_money = "🟢 INSTITUTIONS BUYING (PUT Writing + Positive Delta)"
        elif "DOWN WIND" in wind_data["wind_state"] or "LONG UNWINDING" in wind_data["wind_state"]:
            smart_money = "🔴 INSTITUTIONS SELLING (CALL Writing + Negative Delta)"
        elif "PREMIUM EATING" in wind_data["wind_state"]:
            smart_money = "⚫ OPTION WRITERS DOMINATING (Theta Decay Trap)"

        return {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "wind_engine": wind_data,
            "smart_money_status": smart_money,
            "insight": "OPTION CHAIN = MARKET DNA"
        }

# --- Quick Test ---
if __name__ == "__main__":
    engine = GVNAiWindEngine()
    
    # Simulating a SHORT COVERING scenario (Price UP, CE OI Unwinding)
    test_result = engine.get_market_dna(
        ltp=25100, vwap=25000, 
        ce_oi=80000, pe_oi=150000, 
        ce_coi=-20000, pe_coi=30000, # CE unwinding (-20k), PE writing (+30k)
        ce_vol=200000, pe_vol=120000, 
        delta=0.65, gamma=0.015, theta=-0.5
    )
    
    print("\n🌪️ GVN OPTION CHAIN WIND ENGINE 🌪️")
    print(json.dumps(test_result, indent=2))
