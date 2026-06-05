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
        self.price_history = {} # Stores LTP history per symbol to detect patterns
        self.swing_history = {} # Stores (type, price) for highs and lows
        self.prev_ltp = {} # Track previous LTP for deltaFlow
        self.delta_flow_history = {} # Stores the history of signed volume delta
        
    def calculate_wind_direction(self, symbol, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta):
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
            
            # --- AI SMART MONEY FLOW (from Pine Script deltaFlow) ---
            if symbol not in self.prev_ltp:
                self.prev_ltp[symbol] = ltp
            if symbol not in self.delta_flow_history:
                self.delta_flow_history[symbol] = deque(maxlen=10)
                
            prev_price = self.prev_ltp[symbol]
            self.prev_ltp[symbol] = ltp
            price_change = ltp - prev_price
            
            # Signed volume delta flow based on spot price movement
            delta_flow = (ce_vol + pe_vol) if price_change >= 0 else -(ce_vol + pe_vol)
            self.delta_flow_history[symbol].append(delta_flow)
            avg_delta = sum(self.delta_flow_history[symbol]) / len(self.delta_flow_history[symbol]) if self.delta_flow_history[symbol] else 0
            flow_text = "BUYERS CONTROL 🟢" if avg_delta > 0 else "SELLERS CONTROL 🔴"
            
            wind_state = "🟡 TRAP / SIDEWAYS"
            
            # --- THE 5 INSTITUTIONAL WIND STATES (with AI Flow Filter) ---
            
            # 1. SHORT COVERING (Price ↑ + CE OI ↓) - confirmed by Buyers Control
            if ltp > vwap and ce_coi < 0 and delta > 0 and avg_delta > 0:
                wind_state = "🚀 SHORT COVERING (Fast Upside)"
                wind_power *= 1.5 # Boost power because shorts are trapped
                
            # 2. LONG UNWINDING (Price ↓ + PE OI ↓) - confirmed by Sellers Control
            elif ltp < vwap and pe_coi < 0 and delta < 0 and avg_delta < 0:
                wind_state = "🩸 LONG UNWINDING (Fast Fall)"
                wind_power *= 1.5 # Boost power because longs are trapped
                
            # 3. BULLISH WIND (UP WIND) - confirmed by Buyers Control
            elif ltp > vwap and pe_coi > ce_coi and delta > 0.2 and gamma > 0.005 and avg_delta > 0:
                wind_state = "🟢 UP WIND (Bullish - PUT Writing)"
                
            # 4. BEARISH WIND (DOWN WIND) - confirmed by Sellers Control
            elif ltp < vwap and ce_coi > pe_coi and delta < -0.2 and gamma > 0.005 and avg_delta < 0:
                wind_state = "🔴 DOWN WIND (Bearish - CALL Writing)"
                
            # 5. THE SMALL SOLDIERS WAR (Micro-Trend Level-to-Level)
            # Elephants are fighting (Massive OI on both sides), but small COI shifts are pushing the price
            elif abs(ce_oi - pe_oi) < (min_oi * 0.30) and abs(delta) < 0.25:
                if pe_coi > (ce_coi * 1.2) and ltp >= vwap and avg_delta > 0:
                    wind_state = "🟡 SLOW UP WIND (Level-to-Level)"
                    wind_power = max(wind_power, 1.0) # Enough power for level-to-level
                elif ce_coi > (pe_coi * 1.2) and ltp <= vwap and avg_delta < 0:
                    wind_state = "🟠 SLOW DOWN WIND (Level-to-Level)"
                    wind_power = max(wind_power, 1.0) # Enough power for level-to-level
                else:
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
                "flow_status": flow_text,
                "avg_delta": round(avg_delta, 2),
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

    def analyze_battle_zone(self, ce_oi, pe_oi, ce_coi, pe_coi):
        """
        Tracks the Soldiers War (Momentum of OI)
        Detects if Support or Resistance is strengthening, weakening, or breaking.
        """
        # Prevent tiny values from creating false signals
        if ce_oi < 1000 or pe_oi < 1000: return "🛡️ HOLDING LINES (Consolidation)"
        
        # Calculate momentum (Step forward / Step backward ratio)
        ce_momentum = ce_coi / ce_oi
        pe_momentum = pe_coi / pe_oi
        
        # 1. Support Breaking (Bulls retreating, Bears advancing)
        if pe_momentum < -0.05 and ce_momentum > 0.05:
            return "🚨 SUPPORT BREAKING (Bulls Retreating, Bears Advancing)"
            
        # 2. Resistance Breaking (Bears retreating, Bulls advancing)
        elif ce_momentum < -0.05 and pe_momentum > 0.05:
            return "🚀 RESISTANCE BREAKING (Bears Retreating, Bulls Advancing)"
            
        # 3. Support Weakening (Bulls scared, Bears aggressive)
        elif pe_momentum < 0.02 and ce_momentum > 0.08:
            return "⚠️ SUPPORT WEAKENING (Heavy Call Writing)"
            
        # 4. Resistance Weakening (Bears scared, Bulls aggressive)
        elif ce_momentum < 0.02 and pe_momentum > 0.08:
            return "⚠️ RESISTANCE WEAKENING (Heavy Put Writing)"
            
        # 5. Intense Battle (Both fighting hard)
        elif ce_momentum > 0.05 and pe_momentum > 0.05:
            return "⚔️ INTENSE BATTLE (Both sides adding troops)"
            
        # 6. Mutual Retreat
        elif ce_momentum < -0.02 and pe_momentum < -0.02:
            return "🏳️ MUTUAL RETREAT (Consolidation/Unwinding)"
            
        return "🛡️ HOLDING LINES (Consolidation)"

    def detect_price_pattern(self, symbol, ltp):
        """
        Price Action Memory Tracker (Smart Money Footprints)
        Detects N-Pattern (Creeping Trend), M-Pattern (Double Top), W-Pattern (Double Bottom)
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.swing_history[symbol] = {"highs": [], "lows": []}
            
        history = self.price_history[symbol]
        history.append(ltp)
        if len(history) > 60: history.pop(0)
        
        # We need at least some data to detect swings
        if len(history) < 10:
            return "SCANNING PATTERNS..."
            
        # Basic Swing Detection (simplified for real-time tracking)
        recent_prices = history[-10:]
        current_max = max(recent_prices)
        current_min = min(recent_prices)
        
        highs = self.swing_history[symbol]["highs"]
        lows = self.swing_history[symbol]["lows"]
        
        # Register new high
        if not highs or current_max > highs[-1] * 1.001:
            highs.append(current_max)
            if len(highs) > 3: highs.pop(0)
            
        # Register new low
        if not lows or current_min < lows[-1] * 0.999:
            lows.append(current_min)
            if len(lows) > 3: lows.pop(0)
            
        # --- PATTERN RECOGNITION LOGIC ---
        if len(highs) >= 2 and len(lows) >= 2:
            h1, h2 = highs[-2], highs[-1]
            l1, l2 = lows[-2], lows[-1]
            
            # 1. N-PATTERN (Bullish Creeping Trend / Ascending Channel)
            if h2 > h1 and l2 > l1:
                return "📈 BULLISH N-PATTERN (Smart Money Accumulation)"
                
            # 2. INVERTED N-PATTERN (Bearish Creeping Trend / Descending Channel)
            elif h2 < h1 and l2 < l1:
                return "📉 BEARISH N-PATTERN (Smart Money Distribution)"
                
            # 3. M-PATTERN (Double Top Reversal)
            elif abs(h2 - h1) / h1 < 0.002 and ltp < l2:
                return "🔴 M-PATTERN REVERSAL (Double Top)"
                
            # 4. W-PATTERN (Double Bottom Reversal)
            elif abs(l2 - l1) / l1 < 0.002 and ltp > h2:
                return "🟢 W-PATTERN REVERSAL (Double Bottom)"
                
        return "⚖️ CONSOLIDATION"

    def get_market_dna(self, symbol, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta):
        """
        Returns full Market DNA Report (Smart Money Tracker)
        """
        wind_data = self.calculate_wind_direction(symbol, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta)
        
        # Smart Money Tracker
        smart_money = "WAITING"
        if "UP WIND" in wind_data["wind_state"] or "SHORT COVERING" in wind_data["wind_state"]:
            smart_money = f"🟢 INSTITUTIONS BUYING (PUT Writing + Positive Delta) | {wind_data['flow_status']}"
        elif "DOWN WIND" in wind_data["wind_state"] or "LONG UNWINDING" in wind_data["wind_state"]:
            smart_money = f"🔴 INSTITUTIONS SELLING (CALL Writing + Negative Delta) | {wind_data['flow_status']}"
        elif "PREMIUM EATING" in wind_data["wind_state"]:
            smart_money = f"⚫ OPTION WRITERS DOMINATING (Theta Decay Trap) | {wind_data['flow_status']}"
        else:
            smart_money = f"🟡 SIDEWAYS / TRAP | {wind_data['flow_status']}"
            
        # Detect Price Action Pattern
        pattern = self.detect_price_pattern(symbol, ltp)
        
        # Battle Zone (Support/Resistance Momentum)
        battle_status = self.analyze_battle_zone(ce_oi, pe_oi, ce_coi, pe_coi)

        return {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "wind_engine": wind_data,
            "smart_money_status": smart_money,
            "price_pattern": pattern,
            "battle_status": battle_status,
            "insight": f"{pattern} | {battle_status} | {wind_data['flow_status']}"
        }

# --- Quick Test ---
if __name__ == "__main__":
    engine = GVNAiWindEngine()
    
    # Simulating a SHORT COVERING scenario (Price UP, CE OI Unwinding)
    test_result = engine.get_market_dna(
        symbol="NIFTY", ltp=25100, vwap=25000, 
        ce_oi=80000, pe_oi=150000, 
        ce_coi=-20000, pe_coi=30000, # CE unwinding (-20k), PE writing (+30k)
        ce_vol=200000, pe_vol=120000, 
        delta=0.65, gamma=0.015, theta=-0.5
    )
    
    print("\n=== GVN OPTION CHAIN WIND ENGINE ===")
    import json
    # Use ascii safe representation for printing to windows console
    print(json.dumps(test_result, indent=2, ensure_ascii=True))
