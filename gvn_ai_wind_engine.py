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
        self.prev_spot = {}
        self.prev_ce_ltp = {}
        self.prev_pe_ltp = {}
        self.dpd_history = {}
        
    def calculate_delta_divergence(self, symbol, spot, ce_ltp, pe_ltp, ce_delta, pe_delta):
        """
        Calculates real-time Delta-Premium Divergence (DPD) to track premium efficiency.
        """
        if ce_ltp <= 0 or pe_ltp <= 0:
            return {"ce_div": 0.0, "pe_div": 0.0, "state": "STABLE"}

        if symbol not in self.prev_spot:
            self.prev_spot[symbol] = spot
            self.prev_ce_ltp[symbol] = ce_ltp
            self.prev_pe_ltp[symbol] = pe_ltp
            self.dpd_history[symbol] = deque(maxlen=5)
            return {"ce_div": 0.0, "pe_div": 0.0, "state": "INITIALIZING"}
            
        prev_s = self.prev_spot[symbol]
        prev_ce = self.prev_ce_ltp[symbol]
        prev_pe = self.prev_pe_ltp[symbol]
        
        # Update cache
        self.prev_spot[symbol] = spot
        self.prev_ce_ltp[symbol] = ce_ltp
        self.prev_pe_ltp[symbol] = pe_ltp
        
        # Spot change
        d_spot = spot - prev_s
        
        # Actual option price changes
        d_ce_actual = ce_ltp - prev_ce
        d_pe_actual = pe_ltp - prev_pe
        
        # Expected changes based on Delta (PE Delta is negative)
        ce_expected = ce_delta * d_spot
        pe_expected = pe_delta * d_spot
        
        # Divergence
        ce_div = d_ce_actual - ce_expected
        pe_div = d_pe_actual - pe_expected
        
        self.dpd_history[symbol].append((ce_div, pe_div))
        
        # Calculate smoothed divergence
        avg_ce_div = sum(x[0] for x in self.dpd_history[symbol]) / len(self.dpd_history[symbol])
        avg_pe_div = sum(x[1] for x in self.dpd_history[symbol]) / len(self.dpd_history[symbol])
        
        state = "STABLE"
        if avg_ce_div < -0.15 and avg_pe_div < -0.15:
            state = "DECAY / IV CRUSH"
        elif avg_ce_div > 0.1 and avg_pe_div < -0.1:
            state = "BULLISH MOMENTUM"
        elif avg_pe_div > 0.1 and avg_ce_div < -0.1:
            state = "BEARISH MOMENTUM"
            
        return {
            "ce_div": round(avg_ce_div, 3),
            "pe_div": round(avg_pe_div, 3),
            "state": state
        }
        
    def calculate_wind_direction(self, symbol, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta, ce_ltp=0, pe_ltp=0, ce_delta=0.5, pe_delta=-0.5):
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
            
            # --- DELTA-PREMIUM DIVERGENCE (DPD) FILTER ---
            dpd_metrics = {"ce_div": 0.0, "pe_div": 0.0, "state": "STABLE"}
            if ce_ltp > 0 and pe_ltp > 0:
                dpd_metrics = self.calculate_delta_divergence(symbol, ltp, ce_ltp, pe_ltp, ce_delta, pe_delta)
                dpd_state = dpd_metrics.get("state", "STABLE")
                
                if dpd_state == "DECAY / IV CRUSH":
                    wind_state = "⚫ PREMIUM EATING (Sideways Market)"
                    wind_power = min(wind_power, 0.5) # Force low power to avoid buy entries
                elif dpd_state == "BULLISH MOMENTUM":
                    if "DOWN" not in wind_state and "UNWINDING" not in wind_state:
                        if wind_state == "🟡 TRAP / SIDEWAYS":
                            wind_state = "🟢 UP WIND (Bullish - DPD Confirmed)"
                        wind_power = max(wind_power * 1.3, 1.3)
                elif dpd_state == "BEARISH MOMENTUM":
                    if "UP" not in wind_state and "COVERING" not in wind_state:
                        if wind_state == "🟡 TRAP / SIDEWAYS":
                            wind_state = "🔴 DOWN WIND (Bearish - DPD Confirmed)"
                        wind_power = max(wind_power * 1.3, 1.3)
            
            # --- GVN LEVEL ACCELERATION PATTERN DETECTION (GAMMA SQUEEZE) ---
            try:
                import shared_data
                from gvn_levels_engine import calculate_gvn_levels
                
                benchmark = shared_data.gvn_915_benchmark.get("NIFTY")
                if benchmark and benchmark.get("captured") and symbol == "NIFTY":
                    high_915 = benchmark.get("high")
                    low_915 = benchmark.get("low")
                    close_915 = benchmark.get("close")
                    idx_levels = calculate_gvn_levels(high_915, low_915, close_915)
                    
                    if idx_levels:
                        i5 = idx_levels.get("i5", 0)
                        i6 = idx_levels.get("i6", 0)
                        
                        # Check NIFTY price between Level 6 (i6) and Level 5 (i5)
                        # 1. Bearish Put Acceleration (Put option premium explodes)
                        if i5 < ltp < i6 and dpd_metrics.get("pe_div", 0) > 0.08:
                            wind_state = "🔴 DOWN WIND (Bearish - PE Acceleration Triggered 🌪️)"
                            wind_power = 2.2
                            trend_type = "🔥 Strong Trend (Gamma Explosion Active)"
                            
                            observation = {
                                "timestamp": datetime.datetime.now().isoformat(),
                                "event": "GVN_PE_LEVEL_ACCELERATION",
                                "index_spot": ltp,
                                "index_level_range": f"i6({i6}) to i5({i5})",
                                "pe_divergence": dpd_metrics.get("pe_div"),
                                "observation": "NIFTY spot is falling towards i5 level while Put premiums are accelerating (PE Gamma Squeeze pattern)."
                            }
                            shared_data.append_ai_memory(observation)
                            logger.info(f"🧠 [AI MEMORY] Saved GVN PE Level Acceleration pattern at NIFTY={ltp}")
                            
                            with open("nse_status.log", "a") as f:
                                f.write(f"{datetime.datetime.now()}: [AI OBSERVATION] PUT LEVEL ACCELERATION DETECTED! Spot: {ltp} is between i6({i6}) and i5({i5}) | PE Div: {dpd_metrics.get('pe_div')}\n")
                                
                        # 2. Bullish Call Acceleration (Call option premium explodes as spot rises from i6 up to i5)
                        elif i6 < ltp < i5 and dpd_metrics.get("ce_div", 0) > 0.08:
                            wind_state = "🟢 UP WIND (Bullish - CE Acceleration Triggered 🌪️)"
                            wind_power = 2.2
                            trend_type = "🔥 Strong Trend (Gamma Explosion Active)"
                            
                            observation = {
                                "timestamp": datetime.datetime.now().isoformat(),
                                "event": "GVN_CE_LEVEL_ACCELERATION",
                                "index_spot": ltp,
                                "index_level_range": f"i6({i6}) to i5({i5})",
                                "ce_divergence": dpd_metrics.get("ce_div"),
                                "observation": "NIFTY spot is rising towards i5 level while Call premiums are accelerating (CE Gamma Squeeze pattern)."
                            }
                            shared_data.append_ai_memory(observation)
                            logger.info(f"🧠 [AI MEMORY] Saved GVN CE Level Acceleration pattern at NIFTY={ltp}")
                            
                            with open("nse_status.log", "a") as f:
                                f.write(f"{datetime.datetime.now()}: [AI OBSERVATION] CALL LEVEL ACCELERATION DETECTED! Spot: {ltp} is between i6({i6}) and i5({i5}) | CE Div: {dpd_metrics.get('ce_div')}\n")
            except Exception as e:
                logger.error(f"Error checking GVN Level Acceleration: {e}")

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
                    "theta_decay_rate": round(theta_decay, 2),
                    "ce_div": dpd_metrics.get("ce_div", 0.0),
                    "pe_div": dpd_metrics.get("pe_div", 0.0),
                    "dpd_state": dpd_metrics.get("state", "STABLE")
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

    def get_market_dna(self, symbol, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta, ce_ltp=0, pe_ltp=0, ce_delta=0.5, pe_delta=-0.5):
        """
        Returns full Market DNA Report (Smart Money Tracker)
        """
        wind_data = self.calculate_wind_direction(symbol, ltp, vwap, ce_oi, pe_oi, ce_coi, pe_coi, ce_vol, pe_vol, delta, gamma, theta, ce_ltp, pe_ltp, ce_delta, pe_delta)
        
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
            
        # Append DPD to smart_money if present
        if ce_ltp > 0 and pe_ltp > 0:
            dpd_state = wind_data.get("metrics", {}).get("dpd_state", "STABLE")
            ce_div = wind_data.get("metrics", {}).get("ce_div", 0.0)
            pe_div = wind_data.get("metrics", {}).get("pe_div", 0.0)
            smart_money += f" | DPD: {dpd_state} (CE:{ce_div} PE:{pe_div})"

        # Detect Price Action Pattern
        pattern = self.detect_price_pattern(symbol, ltp)
        
        # Battle Zone (Support/Resistance Momentum)
        battle_status = self.analyze_battle_zone(ce_oi, pe_oi, ce_coi, pe_coi)

        # --- DIRECTION DETAILS (DNA EXTRACTION) ---
        wind_state_upper = wind_data["wind_state"].upper()
        if any(w in wind_state_upper for w in ["UP WIND", "SHORT COVERING", "SLOW UP"]):
            direction = "UP 🟢"
        elif any(w in wind_state_upper for w in ["DOWN WIND", "LONG UNWINDING", "SLOW DOWN"]):
            direction = "DOWN 🔴"
        else:
            direction = "SIDEWAYS / NEUTRAL 🟡"

        # Compare Change in OI (COI)
        if pe_coi > ce_coi:
            oi_growth = "Put Writing (PE) is increasing more 🟢"
            strength_side = "Bulls (Put Writers) are gaining strength 💪"
        elif ce_coi > pe_coi:
            oi_growth = "Call Writing (CE) is increasing more 🔴"
            strength_side = "Bears (Call Writers) are gaining strength 💪"
        else:
            oi_growth = "Call and Put writing increasing equally ⚖️"
            strength_side = "Balanced / Neutral ⚖️"

        # Support vs Resistance movement based on Change in OI
        if pe_coi > 0 and ce_coi > 0:
            if pe_coi > ce_coi:
                sr_movement = "Support is increasing more than Resistance (Put Writing Dominant) 🟢"
            elif ce_coi > pe_coi:
                sr_movement = "Resistance is increasing more than Support (Call Writing Dominant) 🔴"
            else:
                sr_movement = "Both Support & Resistance are increasing equally ⚖️"
        elif pe_coi > 0 and ce_coi <= 0:
            sr_movement = "Support is increasing 🟢 (Resistance is decreasing/unwinding)"
        elif ce_coi > 0 and pe_coi <= 0:
            sr_movement = "Resistance is increasing 🔴 (Support is decreasing/unwinding)"
        else:
            sr_movement = "Both Support & Resistance are decreasing (Option Unwinding) ⚖️"
            
        direction_details = {
            "direction": direction,
            "oi_growth": oi_growth,
            "strength_side": strength_side,
            "sr_movement": sr_movement
        }
 
        return {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "wind_engine": wind_data,
            "smart_money_status": smart_money,
            "price_pattern": pattern,
            "battle_status": battle_status,
            "insight": f"{pattern} | {battle_status} | {wind_data['flow_status']}",
            "direction_details": direction_details
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
