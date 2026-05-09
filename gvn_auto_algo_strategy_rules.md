# GVN Master Auto-Algo: Core Strategy & Rules

This document serves as the "Saving Memory" for the GVN Master Auto-Algo technology. It outlines the exact rule-set derived from real-market observations of the Pine Script levels (i0-i7) and the Delta-Gamma momentum patterns.

## 1. Strike Selection (Delta Filter)
The algorithm will automatically filter and prioritize option strikes based on the following Delta ranges:
*   **Normal Trading Days:** Select strikes with a **Delta of 60 (Range: 0.60 to 0.69)**. This provides the best balance of momentum and premium decay.
*   **Expiry Days (Zero-to-Hero):** Shift priority to strikes with a **Delta of 40 to 50 (Range: 0.40 to 0.50)**. These out-of-the-money or at-the-money strikes provide maximum Gamma blast potential for Z-to-H setups.

## 2. i-Level Priority, Entry Zones & Color Codes
The system will monitor 14 option strikes and react exactly at these pre-calculated 9:15 AM Master Levels (High-Low Fibonacci calculations):

*   **Level i5 (0.5 Fib / 50%) - BLUE LINE 🔵**
    *   **Priority:** First Entry (Morning Momentum).
    *   **Behavior:** The market frequently bounces exactly from this 0.50 level in the morning. The algorithm will set primary alerts here to catch the first major reversal or momentum wave.

*   **Level i7 (0.786 Fib) - BLACK LINE ⚫**
    *   **Priority:** Second Entry (Afternoon / Pullback).
    *   **Behavior:** Used for second entries or deep pullbacks when the first momentum wave is missed or a second setup forms.

*   **Level i1 (1.0 Fib) - GREEN LINE 🟢**
    *   **Priority:** Zero-to-Hero (Expiry Special).
    *   **Behavior:** On expiry days, if the price drops to the i1 level, the algorithm will activate the Z-to-H mode. This level historically triggers massive short-covering or gamma bursts.

## 3. Automation & Execution Pipeline
1.  **9:15 AM Calculation (Data Retrieval):** 
    *   The algo will use **Angel One's Historical API (`getCandleData`)** to fetch the 5-minute candle for the selected strike at exactly 9:15 AM.
    *   *Fallback:* If the 5-min candle is delayed, it will fetch 1-min candles from 9:15 to 9:19 and aggregate the High and Low.
    *   This High and Low will be passed into the Fibonacci formula to calculate the Master Levels (i0-i7).
2.  **Strike Application:** Apply these exact mathematical levels to the 1 selected Option Strike (CE or PE based on Long Buildup).
3.  **Alert Monitoring:** Run a continuous loop scanning for `LTP == i-Level`.
4.  **Auto-Execution (Broker + Demo):**
    *   When an alert triggers, immediately construct the trade JSON.
    *   Send the order directly to **Angel One** (or the selected broker) for instant execution.
    *   Simultaneously log the trade in the **GVN Demo Account** for paper-trading validation.
    *   The system will automatically attach Target and Stop-Loss (e.g., Fixed SL) to the order.

---
*Status: Strategy locked in memory. Waiting for user screenshots to fine-tune the precise reversal behavior at i5, i7, and i1.*
