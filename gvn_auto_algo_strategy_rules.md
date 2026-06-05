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

## 3. Expiry Zero-to-Hero (Z-to-H) Reversal Rules
*   **Qualification Condition:** An option contract (Delta 0.46 to 0.60) qualifies for the Zero-to-Hero watchlist if its 9:15 AM candle low value drops below **Level i7 (Black Line / 0.220 Fib)**.
*   **Entry Trigger:** The algorithm waits for the price to drop near **Level i1 (Green Line / 1.0 Fib / Bottom Level)** (with a ±3.0 point tolerance buffer) and checks that the **Wind Direction** is aligned (UP WIND for CE, DOWN WIND for PE) and not in a Trap/Premium Eating zone.
*   **Targets & Reversal Wave:**
    *   **Target 1:** Level i7 (0.220 Fib)
    *   **Target 2:** Level i6 (0.382 Fib)
    *   **Target 3:** Level i5 (0.50 Fib / Blue Line)
*   **Stop Loss:** A strict 12.0 point stop loss below the entry price.

## 4. Automation & Execution Pipeline
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

## 5. Morning Candle Retracement & Wind Direction Rules (Red vs Green Candle Setup)
These rules are used to identify the morning wind direction and select entries based on the first candle's high/low wicks:

*   **Red Candle Setup (High Wick Retracement):**
    *   **Focus:** Track the candle's High value.
    *   **Condition:** If the High value resides between **Level 0.618** and **Level 0.5**, check if the Put side's **0.618 level** (or **0.7 level** depending on the market open) gets activated.
    *   **Execution:**
        *   *Entry:* Enter after the price crosses **Level 0.5**.
        *   *Targets:* Target 1 is **Level 0.382**, and Target 2 is **Level 0.236** on the Put side.
    *   *Retracement Box:* `0.7` ➔ `0.618` ➔ `0.5` ➔ `0.382`.

*   **Green Candle Setup (Low Wick Retracement):**
    *   **Focus:** Track where the Lower Wick starts and touches.
    *   **Condition:** Check the proximity of the low wick to the four core lines (`0.7`, `0.618`, `0.5`, `0.382`). Verify if it touches **Level 0.7 (Black Line)** or **Level 0.618**.
    *   **Execution:**
        *   *Confirmation:* Ensure the price crosses and sustains above **Level 0.5**.
        *   *Targets:* Target 1 is **Level 0.382**, and Target 2 is **Level 0.236**.


## 6. Real-Market Case Studies & Observations

*   **Case 1: Red Candle Setup (June 5, 2026)**
    *   **Main Index (NIFTY):** The morning candle high touched the **0.618 (23551.48)** level and reversed down.
    *   **Call Option (23200 CE):** Did not touch its 0.6 level (310.76) in the morning ("Morning not touch 0.618 level").
    *   **Put Option (23500 PE):** Dropped and touched its **0.6 level (135.61)** in the morning, finding perfect support and reversing upwards (rallying past 184.65).
    *   **Key Lesson:** In a Red Candle setup, the Put option's 0.6 level serves as a high-probability bounce entry point.

*   **Case 2: Green Candle Setup (June 4, 2026)**
    *   **Main Index (NIFTY):** The morning candle low touched the **0.786 (23140.56)** level, creating a long lower wick.
    *   **Call Option (SENSEX CALL 74400 / NIFTY Delta 60 Call):** Since the main index took support at its lower wick, we monitor the **0.7 and 0.6 levels on the Call side** ("observe Call side Delta 60 strike 0.7 0.6").
    *   **Execution:** The Call option touched its bottom base level (marked ①) and reversed upwards.
    *   **Targets:** The primary target for the Call option is **0.786** (with further targets at 0.5 and 0.382 on the index).
    *   **Key Lesson:** In a Green Candle setup, observe the Call side Delta 60 strike at 0.7/0.6 levels for target wind direction when the main index first candle touches its low.

---
*Status: Strategy locked in memory. Zero-to-Hero, Morning Retracement, and Real-Market Case Studies fully integrated.*


