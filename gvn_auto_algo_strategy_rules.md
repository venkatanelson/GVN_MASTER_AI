# GVN Master Auto-Algo: Core Strategy & Rules

This document serves as the "Saving Memory" for the GVN Master Auto-Algo technology. It outlines the exact rule-set derived from real-market observations of the Pine Script levels (i0-i7) and the Delta-Gamma momentum patterns.

---

## 1. Core Formulas & Strategy Names

We categorize our key trading setups into three official formulas:

### 🚀 Formula 1: GVN Expiry Zero-to-Hero (Z2H Expiry Blast)
*   **Target Day:** Expiry Days only.
*   **Strike Selection:** Strikes with a **Delta of 40 to 85 (Range: 0.40 to 0.85)** (expanded to include ITM/ATM strikes like SENSEX 77000 CE and 77200 CE).
*   **Qualification Condition:** Option contract qualifies for the watchlist if its 9:15 AM candle low drops below **Level i7 (Black Line / 0.220 Fib)**.
*   **Entry Trigger:** Price drops near **Level i1 (Green Line / 1.0 Fib / Bottom Level)** (±3.0 point buffer) with multi-layer confirmation filters.
*   **Multi-Layer Confirmations:**
    *   **Wind Direction Alignment:** Must align with trade bias (Bullish winds: UP WIND, SHORT COVERING, SLOW UP for CE; Bearish winds: DOWN WIND, LONG UNWINDING, SLOW DOWN for PE).
    *   **Wind Power & Volume:** Minimum Wind Power must be **>= 0.8** (verifying strong institutional volume/pressure).
    *   **Anti-Trap Filter:** Entry is rejected if `TRAP` or `PREMIUM EATING` is detected in the wind direction.
    *   **Trend Confirmation:** Overall index trend must not be opposing (CE trades blocked in strong bearish trend; PE trades blocked in strong bullish trend).
    *   **Morning Wick Confirmation:** Morning candle wick must match the retracement zone on the index (high wick for PE, low wick for CE).
    *   **Wind Direction Sentinel Sync (Delta-60 Confirmation):** 
        *   Before executing a Z2H CE trade, the corresponding Delta-60 CE contract must have crossed and held above its **0.6 and 0.5 GVN levels** (under Formula 4). If the Delta-60 CE is trading below its 0.6 level, the Z2H CE trade is blocked.
        *   Before executing a Z2H PE trade, the corresponding Delta-60 PE contract must have crossed and held above its **0.6 and 0.5 GVN levels**. If the Delta-60 PE is trading below its 0.6 level, the Z2H PE trade is blocked.
        *   This ensures Z2H entries are backed by verified institutional volume pressure.
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
*   **Official Wind Direction Name:** `Morning Retracement Wind` (or `MRV Wind`)
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
*   **GVN Dual-Sync Timing & Level Comparison Filter:**
    *   **Timing Correlation:** Compare the exact time when the Main Index touches/crosses a level with when the Option Premium touches/crosses its corresponding level (e.g. `12:25 PM` candle analysis).
    *   **Divergence Filter:** If the Main Index reaches/crosses its `0.5` level but the active Option contract (CE/PE) remains below/fails to cross its own `0.5` level, the move is a **false breakout** (Reject Entry).
    *   **PE Acceleration Trigger:** When Nifty Index breaks below its `0.5` level (`23,969.03`) and the Put Option simultaneously crosses above its `0.5` level (`197.66`), it triggers a high-probability **2x Momentum Breakout Entry** targeting `i3 (234.84)`.

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

### 🧭 Formula 4: GVN Wind Direction Sentinel (Delta-60 Trend Lock & Reversal)
This formula uses Delta-60 option contracts and index Fibonacci levels to identify the dominant trend at market open and capture high-probability afternoon reversals.
*   **Strike Selection:** Option contracts with a **Delta of 0.59 to 0.69 (Delta-60)** at market open.
*   **Morning Trend Lock & Pressure Analysis (9:15 AM Candle Signature):**
    *   Compare the 9:15 AM candle behavior between CE and PE to determine the direction of institutional pressure:
        *   **Strong Side (Bullish PE / Bearish Market):** PE candle starts near the bottom levels (between 0.7 and 0.6 GVN levels) and prints a strong, full-bodied **green candle** crossing above the **0.6 GVN level** from below, backed by high volume (e.g. 2x margin volume). The exact retracement (50% or 80%) doesn't matter; the break and close above the 0.6/0.5 levels confirm the trend.
        *   **Weak Side (Bearish CE):** CE candle starts near upper levels (between 0.3 and 0.2 GVN levels) and prints a **red candle** cutting down horizontally through the **0.5 GVN level** and closing below it, without ever touching its 0.6 level.
    *   **Asymmetric Level Retest Rule:** If one side (e.g., PE) touches or crosses its 0.6 or 0.7 level from below, but the opposite side (CE) does not touch its corresponding GVN level, the market pressure is locked on the side that successfully tested/broke its levels.
    *   **Option Chain OI % Asymmetry Surge Rule (Institutional Lock Filter):**
        *   **Bullish Surge:** When Put Option strikes (e.g. 24150, 24250, 24350) display a massive **+2,000% to +7,000%+** positive OI Change % surge (heavy Put Writing) accompanied by Put price decay (-50% to -60%), while Call side shows negative OI % (unwinding) or significantly lower OI % build-up, the Wind Sentinel locks **+100% BULLISH WIND DIRECTION**. This confirms institutional support floor and predicts Spot index expansion towards higher targets (e.g. 24300 - 24350+).
        *   **Bearish Surge:** When Call Option strikes display a **+2,000% to +7,000%+** positive OI Change % surge with Call price decay while Put side unwinds, the Wind Sentinel locks **-100% BEARISH WIND DIRECTION**.
*   **Anti-Trap Rule (Trend Filter):**
    *   No trades are allowed on the opposite side as long as the dominant side stays above its 0.5 level.
    *   Opposite option trade is blocked if it remains below its 0.6 and 0.5 levels.
*   **Afternoon Reversal Trigger:**
    *   Triggered in the afternoon (12:30 PM - 3:00 PM) when the Main Index crosses its **0.618 Fib level** from below.
    *   Simultaneously, the opposite option must cross its dormant **0.6 GVN level** from below, and confirm above **0.5 GVN level**.
    *   This triggers a high-probability trade targeting the **0.3 GVN level** (and 0.2 level).
*   **Targets:** Level 0.3 (0.382 Fib) and Level 0.2 (0.236 Fib).
*   **Stop Loss:** Strict 12.0 point stop loss.

---

### 📉 Formula 5: GVN RSI-50 Gravity Retracement Sync (Level Continuation Lock)
This formula maps the index and active option strike to identify continuation and re-entry trade setups when the pullback is clean and backed by RSI midline support.
*   **Trend Confirmation:** Nifty Spot is trading in a clean channel (e.g. above its 50% midpoint).
*   **Option Setup:** Option premium has broken out above a key GVN level (e.g., Target 1 / Level i6 or Level i7) and takes support (holds above it) during a pullback.
*   **Continuation Trigger:** Trigger a continuation trade when the **Option RSI 14 pulls back to exactly the 50 midline (RSI 50 Retracement) and bounces**, validating that the breakout momentum is intact.
*   **Target:** Next higher GVN level.
*   **Stop Loss:** Strict 12.0 point stop loss.

---

### 📊 Formula 6: GVN QQE MOD + RSI-15 Volume Divergence (Trend Breakout / Reversal)
This formula uses a combination of QQE MOD, smoothed RSI, and 2x volume pressure to confirm true breakouts and detect early reversals from fake breakouts.
*   **Indicator Configurations (QQE MOD):**
    *   *Primary QQE:* RSI Length 6, Smoothing 5, Factor 3.0, Threshold 3.0.
    *   *Secondary QQE:* RSI Length 6, Smoothing 5, Factor 1.61, Threshold 3.0.
    *   *Bollinger Bands of Primary QQE:* Length 50, Multiplier 0.35.
*   **RSI 15 Confirmation & Volume Spike:**
    *   Breakout requires the Option RSI 14 (computed over 15 closed candle points, referred to as RSI-15) to cross above the 50 midline and hold, accompanied by a volume spike of **>= 2x average volume**.
*   **QQE MOD Signal Validation:**
    *   *Bullish (QQE Up):* Secondary RSI Histogram - 50 > 3.0 and Primary QQE Trend Line - 50 > Bollinger Upper Band.
    *   *Bearish (QQE Down):* Secondary RSI Histogram - 50 < -3.0 and Primary QQE Trend Line - 50 < Bollinger Lower Band.
*   **RSI 50 Divert (Fake Breakout / Reversal Confirmation):**
    *   If an option strike (e.g., PE) attempts to break above 50 on RSI but gets rejected/diverted downwards (turns back below 50, e.g. from 48-52 range back to under 47) even though volume is green and above the line:
        *   This is a **best confirmation** of PE side weakness and momentum failure.
        *   It confirms a high-probability CALL-side (CE) breakout, especially when spot support is verified (e.g., at round-number strikes like 24000, 24100, 24150).
        *   The algorithm blocks PE trades and prioritizes or triggers a CE entry.
*   **Targets:** Next key GVN level (e.g., Level i3 or Level i2).
*   **Stop Loss:** Strict 12.0 point stop loss.

---
*Status: Strategy locked in memory. Formula 1 (Zero-to-Hero), Formula 2 (Level Acceleration with Gamma Physics), Formula 3 (9:15 Option Level Confirmation), Formula 4 (Wind Direction Sentinel), Formula 5 (RSI-50 Gravity Retracement Sync), and Formula 6 (QQE MOD + RSI-15 Volume Divergence) fully saved.*



