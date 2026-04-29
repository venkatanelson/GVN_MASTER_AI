"""
GVN AI Sentiment Engine: Institutional Flow Detection & Fake Signal Filter
Detects "Big Boys Buying/Selling" using Volume Delta, Put-Call Ratio, and Time-Zone Momentum
"""

import logging
from datetime import datetime, timedelta
from collections import deque
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AISentimentEngine")


# ───────────────────────────────────────────────────────────────
# VOLUME DELTA & PUT-CALL RATIO ANALYZER
# ───────────────────────────────────────────────────────────────

class VolumeDeltaAnalyzer:
    """Detect institutional buying/selling through volume analysis"""
    
    def __init__(self, lookback_candles=20):
        self.lookback = lookback_candles
        self.volume_history = deque(maxlen=lookback_candles)
        self.price_history = deque(maxlen=lookback_candles)
        self.direction_history = deque(maxlen=lookback_candles)
    
    def update_candle(self, price, volume, direction="UP"):
        """Record candle data (UP/DOWN based on close vs open)"""
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.direction_history.append(direction)
    
    def calculate_volume_delta(self):
        """Calculate Volume Delta = Σ(Volume if UP) - Σ(Volume if DOWN)"""
        up_volume = sum(vol for vol, direction in zip(self.volume_history, self.direction_history) if direction == "UP")
        down_volume = sum(vol for vol, direction in zip(self.volume_history, self.direction_history) if direction == "DOWN")
        delta = up_volume - down_volume
        return delta, up_volume, down_volume
    
    def get_volume_trend(self):
        """Trend: Bullish if up_volume > 60% of total"""
        if len(self.volume_history) < 3:
            return "NEUTRAL"
        
        delta, up_vol, down_vol = self.calculate_volume_delta()
        total_vol = up_vol + down_vol
        
        if total_vol == 0:
            return "NEUTRAL"
        
        up_ratio = up_vol / total_vol
        
        if up_ratio > 0.65:
            return "🟢 BULLISH (Institutional Buying)"
        elif up_ratio < 0.35:
            return "🔴 BEARISH (Institutional Selling)"
        else:
            return "🟡 NEUTRAL"
    
    def detect_volume_spike(self, threshold_multiplier=1.5):
        """Detect if current volume is 1.5x average"""
        if len(self.volume_history) < 5:
            return False, 1.0
        
        avg_vol = sum(list(self.volume_history)[:-1]) / (len(self.volume_history) - 1)
        current_vol = self.volume_history[-1] if self.volume_history else 0
        
        spike_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        is_spike = spike_ratio >= threshold_multiplier
        
        return is_spike, spike_ratio


# ───────────────────────────────────────────────────────────────
# PUT-CALL RATIO SENTIMENT
# ───────────────────────────────────────────────────────────────

class PutCallRatioAnalyzer:
    """Analyze Put-Call ratio to detect institutional sentiment"""
    
    @staticmethod
    def calculate_pcr(put_volume, call_volume):
        """PCR = Put Volume / Call Volume"""
        if call_volume == 0:
            return 0.0
        return put_volume / call_volume
    
    @staticmethod
    def interpret_pcr(pcr):
        """
        PCR > 1.0 = More puts = Bearish sentiment (hedging)
        PCR < 1.0 = More calls = Bullish sentiment (buying)
        """
        if pcr > 1.2:
            return "🔴 BEARISH", "Heavy put buying (Fear)"
        elif pcr > 0.8:
            return "🟡 NEUTRAL", "Balanced put-call"
        elif pcr < 0.6:
            return "🟢 BULLISH", "Heavy call buying (Greed)"
        else:
            return "🟡 NEUTRAL", "Slightly bullish"
    
    @staticmethod
    def get_pcr_trend(alpha_grid):
        """Calculate PCR from alpha grid"""
        if not alpha_grid:
            return None, None, None
        
        call_volume = sum(c.get("volume", 0) for c in alpha_grid.get("calls", []))
        put_volume = sum(p.get("volume", 0) for p in alpha_grid.get("puts", []))
        
        pcr = PutCallRatioAnalyzer.calculate_pcr(put_volume, call_volume)
        sentiment, reason = PutCallRatioAnalyzer.interpret_pcr(pcr)
        
        return pcr, sentiment, reason


# ───────────────────────────────────────────────────────────────
# TIME-ZONE MOMENTUM DETECTOR
# ───────────────────────────────────────────────────────────────

class TimeZoneMomentum:
    """Detect momentum based on market session and time zones"""
    
    IST_MARKET_HOURS = {
        "open": 9.25,      # 09:15 IST
        "mid": 12.5,       # 12:30 IST (Mid-morning spike)
        "lunch": 13.5,     # 13:30 IST (Lunch resistance)
        "close": 15.25,    # 15:15 IST (Close volatility)
    }
    
    @staticmethod
    def get_current_session():
        """Determine current market session"""
        now = datetime.now()
        hour = now.hour + now.minute / 60
        
        if 9.25 <= hour < 10.5:
            return "OPENING (9:15-10:30)", "HIGH_VOLATILITY"
        elif 10.5 <= hour < 12.5:
            return "MID_MORNING (10:30-12:30)", "MEDIUM"
        elif 12.5 <= hour < 13.5:
            return "LUNCH (12:30-13:30)", "CONSOLIDATION"
        elif 13.5 <= hour < 15.0:
            return "AFTERNOON (13:30-15:00)", "TRENDING"
        elif 15.0 <= hour < 15.3:
            return "CLOSE_HOUR (15:00-15:15)", "PEAK_VOLATILITY"
        elif 15.3 <= hour < 16.0:
            return "AFTER_CLOSE (15:15-16:00)", "FINAL_SWEEP"
        else:
            return "AFTER_MARKET", "QUIET"
    
    @staticmethod
    def get_session_momentum():
        """Get momentum multiplier based on session"""
        session, volatility = TimeZoneMomentum.get_current_session()
        
        momentum_map = {
            "OPENING (9:15-10:30)": (1.5, "🔴 PEAK: Opening breakout energy"),
            "MID_MORNING (10:30-12:30)": (1.2, "🟠 MEDIUM: Trend establishing"),
            "LUNCH (12:30-13:30)": (0.7, "🟡 LOW: Consolidation phase"),
            "AFTERNOON (13:30-15:00)": (1.3, "🟢 HIGH: Institutional trading"),
            "CLOSE_HOUR (15:00-15:15)": (1.8, "🔴 PEAK: Close volatility burst"),
            "AFTER_CLOSE (15:15-16:00)": (0.9, "🟡 MEDIUM: Final liquidity"),
            "AFTER_MARKET": (0.3, "⚫ DEAD: No volatility")
        }
        
        return momentum_map.get(session, (1.0, "❓ UNKNOWN"))
    
    @staticmethod
    def is_prime_trading_window():
        """Check if current time is prime trading window (Peak institutional activity)"""
        session, _ = TimeZoneMomentum.get_current_session()
        prime_windows = [
            "OPENING (9:15-10:30)",      # RTH opening
            "CLOSE_HOUR (15:00-15:15)"   # Close hour gamma burst
        ]
        return session in prime_windows


# ───────────────────────────────────────────────────────────────
# INSTITUTIONAL FLOW DETECTOR (BIG BOYS TRACKER)
# ───────────────────────────────────────────────────────────────

class InstitutionalFlowDetector:
    """Detect institutional (Big Boys) buying/selling patterns"""
    
    def __init__(self):
        self.flow_history = deque(maxlen=50)
        self.cumulative_flow = 0
    
    def analyze_flow(self, alpha_grid, volume_delta):
        """
        Detect institutional flow from:
        1. Put-Call Ratio extremes
        2. High volume on specific strikes
        3. Gamma concentration
        """
        if not alpha_grid:
            return None
        
        pcr, pcr_sentiment, pcr_reason = PutCallRatioAnalyzer.get_pcr_trend(alpha_grid)
        
        # Identify max gamma strike (institutional target)
        max_gamma_call = max(alpha_grid.get("calls", []), key=lambda x: x.get("gamma", 0), default=None)
        max_gamma_put = max(alpha_grid.get("puts", []), key=lambda x: x.get("gamma", 0), default=None)
        
        flow_signal = {
            "timestamp": datetime.now().isoformat(),
            "pcr": pcr,
            "pcr_sentiment": pcr_sentiment,
            "volume_delta": volume_delta,
            "max_gamma_call": max_gamma_call["strike"] if max_gamma_call else 0,
            "max_gamma_put": max_gamma_put["strike"] if max_gamma_put else 0,
            "flow_direction": "BULLISH" if volume_delta > 0 else "BEARISH"
        }
        
        self.flow_history.append(flow_signal)
        self.cumulative_flow += volume_delta
        
        return flow_signal
    
    def detect_reversal(self):
        """Detect trend reversal (Fake signal warning)"""
        if len(self.flow_history) < 5:
            return False, None
        
        recent_flows = list(self.flow_history)[-5:]
        recent_directions = [f.get("flow_direction") for f in recent_flows]
        
        # Reversal if last 3 differ from first 2
        if len(set(recent_directions[-3:])) > len(set(recent_directions[:2])):
            return True, "⚠️ REVERSAL DETECTED: Flow direction changed"
        
        return False, None


# ───────────────────────────────────────────────────────────────
# UNIFIED SENTIMENT FILTER
# ───────────────────────────────────────────────────────────────

class UnifiedSentimentFilter:
    """Combined AI sentiment analysis for fake signal filtering"""
    
    def __init__(self):
        self.vol_analyzer = VolumeDeltaAnalyzer(lookback_candles=20)
        self.flow_detector = InstitutionalFlowDetector()
    
    def get_full_sentiment(self, alpha_grid, price, volume, price_direction="UP"):
        """Get complete sentiment analysis"""
        
        # Update volume data
        self.vol_analyzer.update_candle(price, volume, price_direction)
        
        # Calculate components
        vol_delta, up_vol, down_vol = self.vol_analyzer.calculate_volume_delta()
        volume_trend = self.vol_analyzer.get_volume_trend()
        is_vol_spike, spike_ratio = self.vol_analyzer.detect_volume_spike()
        
        # Put-Call analysis
        pcr, pcr_sentiment, pcr_reason = PutCallRatioAnalyzer.get_pcr_trend(alpha_grid)
        
        # Institutional flow
        flow = self.flow_detector.analyze_flow(alpha_grid, vol_delta)
        is_reversal, reversal_msg = self.flow_detector.detect_reversal()
        
        # Time-zone momentum
        session, volatility = TimeZoneMomentum.get_current_session()
        momentum, momentum_desc = TimeZoneMomentum.get_session_momentum()
        is_prime = TimeZoneMomentum.is_prime_trading_window()
        
        # Generate final signal
        sentiment_score = 0
        
        # Add points for bullish factors
        if "BULLISH" in volume_trend:
            sentiment_score += 2
        if pcr and pcr < 0.8:
            sentiment_score += 1.5
        if is_vol_spike and spike_ratio > 2.0:
            sentiment_score += 1
        if is_prime:
            sentiment_score += 1
        
        # Subtract points for bearish/warning factors
        if is_reversal:
            sentiment_score -= 2
        if pcr and pcr > 1.2:
            sentiment_score -= 1.5
        
        # Final verdict
        if sentiment_score > 3:
            verdict = "🟢 STRONG BUY (Institutional Buying)"
        elif sentiment_score > 1:
            verdict = "🟡 MILD BUY"
        elif sentiment_score < -3:
            verdict = "🔴 STRONG SELL (Institutional Selling)"
        elif sentiment_score < -1:
            verdict = "🟠 MILD SELL"
        else:
            verdict = "⚫ NEUTRAL (Hold/Wait)"
        
        # Check for fake signals
        is_fake_breakout = is_reversal or (pcr and pcr > 1.2 and volume_trend == "🟢 BULLISH (Institutional Buying)")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "verdict": verdict,
            "score": round(sentiment_score, 2),
            "components": {
                "volume_trend": volume_trend,
                "volume_spike": f"{'YES' if is_vol_spike else 'NO'} ({spike_ratio:.2f}x)",
                "pcr": round(pcr, 3) if pcr else 0,
                "pcr_sentiment": pcr_sentiment,
                "session": session,
                "momentum": momentum,
                "momentum_desc": momentum_desc,
                "prime_window": "YES" if is_prime else "NO"
            },
            "warnings": {
                "is_reversal": is_reversal,
                "reversal_msg": reversal_msg,
                "is_fake_breakout": is_fake_breakout,
                "institutional_flow": flow.get("flow_direction") if flow else "NEUTRAL"
            }
        }


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Initialize sentiment filter
    sentiment = UnifiedSentimentFilter()
    
    # Mock alpha grid (same structure as Greeks engine output)
    mock_grid = {
        "calls": [
            {"strike": 25000, "volume": 5000, "gamma": 0.001},
            {"strike": 25100, "volume": 8000, "gamma": 0.0015},
            {"strike": 25200, "volume": 3000, "gamma": 0.0005},
        ],
        "puts": [
            {"strike": 25000, "volume": 6000, "gamma": 0.0012},
            {"strike": 24900, "volume": 4000, "gamma": 0.0008},
            {"strike": 24800, "volume": 2000, "gamma": 0.0003},
        ]
    }
    
    # Simulate multiple candles
    for i in range(10):
        result = sentiment.get_full_sentiment(
            mock_grid,
            price=25000 + i*10,
            volume=1000000 * (1 + i*0.1),
            price_direction="UP" if i % 2 == 0 else "DOWN"
        )
        
        if i == 9:
            print("\n✅ AI Sentiment Engine Initialized")
            print(json.dumps(result, indent=2))
