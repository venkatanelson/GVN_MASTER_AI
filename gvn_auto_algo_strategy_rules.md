# GVN Master Auto-Algo: Core Strategy & Rules

This document serves as the "Saving Memory" for the GVN Master Auto-Algo technology. It outlines the exact rule-set derived from real-market observations of the Pine Script levels (i0-i7) and the Delta-Gamma momentum patterns.

---

## 1. Core Formulas & Strategy Names

We categorize our key trading setups into three official formulas:

### 🚀 Formula 1: GVN Expiry Zero-to-Hero (Z2H Expiry Blast)
*   **Target Day:** Expiry Days only.
*   **Strike Selection:** Strikes with a **Delta of 40 to 50 (Range: 0.40 to 0.50)**.
*   **Qualification Condition:** Option contract qualifies for the watchlist if its 9:15 AM candle low drops below **Level i7 (Black Line / 0.220 Fib)**.
*   **Entry Trigger:** Price drops near **Level i1 (Green Line / 1.0 Fib / Bottom Level)** (±3.0 point buffer) with wind alignment, and no traps.
*   **Targets:** 
    *   Target 1: Level i7 (0.220 Fib)
    *   Target 2: Level i6 (0.382 Fib)
    *   Target 3: Level i5 (0.50 Fib / Blue Line)
*   **Stop Loss:** Strict 12.0 point stop loss.

---

### 🌪️ Formula 2: GVN Level Acceleration (Gamma Squeeze Reversal)
This formula is triggered by index reversals that cause massive option premium jumps due to accelerated option Greeks.
*   **Index Condition:** Main index spot is reversing and moving between **Level 6 (0.618 Fib / idx_i3)** and **Level 5 (0.50 Fib / idx_i5)**.
*   **Option Trigger:** Option LTP touches its launchpad **Level 7 (0.786 Fib)** and breaks above **Level 6**.
*   **Greeks & Gamma Physics:**
    *   **OTM to ATM (Level 7 to Level 5):** As the option price rises from Level 7 and crosses Level 6 towards Level 5, it transitions from Out-of-the-Money (OTM) to At-the-Money (ATM).
    *   **Peak Gamma:** At Level 5 (ATM), **Gamma reaches its absolute peak**. High Gamma means Delta changes at its fastest rate. This causes the option premium to accelerate rapidly, covering three option levels (Level 7 ➔ Level 6 ➔ Level 5) while the index only moves one level.
    *   **ATM to ITM (Above Level 5):** Once Level 5 is crossed, the option becomes In-the-Money (ITM). Gamma decreases, but **Delta approaches 1.0**, causing the option premium to move point-for-point (1:1 ratio) with the index, blasting to Target Level 3 and beyond.
*   **Targets:** Target Level 3 (0.382 Fib).
*   **Stop Loss:** Strict 12.0 point stop loss.

---

### 🟢 Formula 3: GVN 9:15 Option Level Confirmation (Morning Retracement Validation)
This formula uses the 9:15 AM candle close and option level retests to establish a high-conviction directional bias.
*   **Call Direction Setup (Bullish):**
    *   **Index Condition:** The 9:15 AM candle closes **above the 0.618 level** (e.g. 25000).
    *   **Option Action (CE):** We verify if the Call Option touches **0.6 level**, crosses **0.5 level**, and then returns to retest/touch **0.7 or 0.6 level**.
    *   **Result:** Confirms strong upward wind direction on the Call side.
*   **Put Direction Setup (Bearish):**
    *   **Index Condition:** The 9:15 AM candle closes **below the 0.5 level** (e.g. 25000).
    *   **Option Action (PE):** We verify if the Put Option touches **0.6 level**, retests it, and then crosses **0.5 or 0.7 level** (checking average levels).
    *   **Result:** Confirms strong downward wind direction on the Put side.
*   **Verification Rule:** Ensure that the index and options are strictly matched (Nifty with Nifty options, Sensex with Sensex options). Never match Sensex options with Nifty index.

---

## 2. i-Level Priority, Entry Zones & Color Codes
The system monitors option strikes and reacts at these 9:15 AM Master Levels:
*   **Level i5 (0.5 Fib / 50%) - BLUE LINE 🔵** (Morning Momentum / First Entry)
*   **Level i7 (0.786 Fib) - BLACK LINE ⚫** (Afternoon Pullback / Second Entry / Level Acceleration Launchpad)
*   **Level i1 (1.0 Fib) - GREEN LINE 🟢** (Zero-to-Hero Expiry Level)

---

## 3. Automation & Execution Pipeline
1.  **9:15 AM Calculation (Data Retrieval):** Fetch 5-minute candle for the selected strike and calculate Fibonacci levels (i0-i7).
2.  **Strict Symbol Alignment:** Ensure option contract matches index spot symbol strictly (prevent Nifty-Sensex mismatch).
3.  **Alert Monitoring:** Run live scan loops matching LTP to levels.
4.  **Auto-Execution:** Dispatch BUY orders to broker and demo accounts.

---

## 4. Real-Market Case Studies & Observations

*   **Case 1: Red Candle Setup (June 5, 2026)**
    *   **Main Index (NIFTY):** Morning candle high touched 0.618 (23551.48) and reversed down.
    *   **Put Option (23500 PE):** Touched 0.6 level (135.61) in the morning, found support, and rallied past 184.65.
*   **Case 2: Green Candle Setup (June 4, 2026)**
    *   **Main Index (NIFTY):** Morning candle low touched 0.786 (23140.56) level.
    *   **Call Option (23200 CE):** Call option touched its bottom base level and reversed upwards, reaching target 0.786.
*   **Case 3: Put Option Level Acceleration / Gamma Squeeze (June 17, 2026)**
    *   **Main Index (NIFTY):** Reversed and fell from Level 6 (0.618 - 24087) to Level 5 (0.50 - 24008).
    *   **Put Option (PE Contract):** PE premium at Level 7 (₹334.13) began an explosive run, crossing Level 6 (₹493.28) and Level 5 (₹609.20), eventually reaching target Level 3 (₹725 / ₹867). This matches **Formula 2 (GVN Level Acceleration)**.

---
*Status: Strategy locked in memory. Formula 1 (Zero-to-Hero), Formula 2 (Level Acceleration with Gamma Physics), and Formula 3 (9:15 Option Level Confirmation) fully saved.*


