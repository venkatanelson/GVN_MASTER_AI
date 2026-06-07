import sys
import os
import unittest
from collections import deque

# Setup path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDPDLogic(unittest.TestCase):
    def setUp(self):
        self.prev_spot = 25000.0
        self.prev_ce_ltp = 150.0
        self.prev_pe_ltp = 150.0
        self.ce_delta = 0.50
        self.pe_delta = -0.50  # PE Delta is negative
        self.dpd_history = deque(maxlen=5)

    def calculate_tick_dpd(self, spot, ce_ltp, pe_ltp):
        d_spot = spot - self.prev_spot
        d_ce_actual = ce_ltp - self.prev_ce_ltp
        d_pe_actual = pe_ltp - self.prev_pe_ltp

        # Expected changes
        ce_expected = self.ce_delta * d_spot
        pe_expected = self.pe_delta * d_spot

        # Divergence
        ce_div = d_ce_actual - ce_expected
        pe_div = d_pe_actual - pe_expected

        # Update cache
        self.prev_spot = spot
        self.prev_ce_ltp = ce_ltp
        self.prev_pe_ltp = pe_ltp

        self.dpd_history.append((ce_div, pe_div))
        avg_ce_div = sum(x[0] for x in self.dpd_history) / len(self.dpd_history)
        avg_pe_div = sum(x[1] for x in self.dpd_history) / len(self.dpd_history)

        state = "STABLE"
        if avg_ce_div < -0.15 and avg_pe_div < -0.15:
            state = "DECAY / IV CRUSH"
        elif avg_ce_div > 0.1 and avg_pe_div < -0.1:
            state = "BULLISH MOMENTUM"
        elif avg_pe_div > 0.1 and avg_ce_div < -0.1:
            state = "BEARISH MOMENTUM"

        return avg_ce_div, avg_pe_div, state

    def test_decay_scenario(self):
        print("\n--- Test Scenario 1: Sideways / Decay / IV Crush ---")
        # Spot is flat at 25000, CE and PE lose 0.5 points per tick
        for i in range(5):
            ce_div, pe_div, state = self.calculate_tick_dpd(25000.0, 150.0 - (0.5 * (i + 1)), 150.0 - (0.5 * (i + 1)))
            print(f"Tick {i+1}: CE Div={ce_div:.2f}, PE Div={pe_div:.2f}, State={state}")
        self.assertEqual(state, "DECAY / IV CRUSH")

    def test_bullish_momentum_scenario(self):
        print("\n--- Test Scenario 2: Bullish Momentum (CE outperforms, PE decays/loses more) ---")
        # Spot goes up by 10 points per tick
        # Expected CE increase = 10 * 0.5 = 5 points per tick. Actual CE increase = 6 points per tick (outperforming)
        # Expected PE decrease = 10 * -0.5 = -5 points per tick. Actual PE decrease = -6 points per tick (decaying/falling faster)
        for i in range(5):
            ce_div, pe_div, state = self.calculate_tick_dpd(25000.0 + (10 * (i + 1)), 150.0 + (6 * (i + 1)), 150.0 - (6 * (i + 1)))
            print(f"Tick {i+1}: CE Div={ce_div:.2f}, PE Div={pe_div:.2f}, State={state}")
        self.assertEqual(state, "BULLISH MOMENTUM")

    def test_bearish_momentum_scenario(self):
        print("\n--- Test Scenario 3: Bearish Momentum (PE outperforms, CE decays/loses more) ---")
        # Spot goes down by 10 points per tick
        # Expected CE change = -10 * 0.5 = -5 points per tick. Actual CE change = -6 points per tick (losing more)
        # Expected PE change = -10 * -0.5 = 5 points per tick. Actual PE change = 6 points per tick (outperforming)
        for i in range(5):
            ce_div, pe_div, state = self.calculate_tick_dpd(25000.0 - (10 * (i + 1)), 150.0 - (6 * (i + 1)), 150.0 + (6 * (i + 1)))
            print(f"Tick {i+1}: CE Div={ce_div:.2f}, PE Div={pe_div:.2f}, State={state}")
        self.assertEqual(state, "BEARISH MOMENTUM")

if __name__ == "__main__":
    unittest.main()
