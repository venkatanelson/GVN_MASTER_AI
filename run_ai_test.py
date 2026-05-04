import sys
import logging
from gvn_ai_delta60_engine import GVNAiDelta60Engine
import nse_option_chain

logging.basicConfig(level=logging.INFO)

print("🚀 Starting GVN AI Progress Report Test...")
ai = GVNAiDelta60Engine()
print("Fetching live option chain for NIFTY...")
chain_response = nse_option_chain.fetch_nse_option_chain("NIFTY")
if not chain_response or "records" not in chain_response:
    print("❌ Failed to fetch option chain from NSE.")
    sys.exit(1)

records = chain_response["records"]
spot_price = records.get("underlyingValue", 25000)
print(f"📊 Current NIFTY Spot Price: {spot_price}")

formatted_chain = {"CE": [], "PE": []}
for item in records.get("data", []):
    if "CE" in item: 
        item["CE"]["option_type"] = "CE"
        formatted_chain["CE"].append(item["CE"])
    if "PE" in item: 
        item["PE"]["option_type"] = "PE"
        formatted_chain["PE"].append(item["PE"])

support, resistance = ai.analyze_support_resistance(formatted_chain)
print(f"🧱 Detected Support (Highest Put OI+Vol): {support}")
print(f"🧱 Detected Resistance (Highest Call OI+Vol): {resistance}")

shift_detected, shift_msg = ai.detect_market_shift(support, resistance)
print(f"🔄 Market Shift Status: {shift_msg}")

best_strike = ai.pick_single_momentum_strike(formatted_chain, spot_price)
if best_strike:
    print(f"🎯 Selected Momentum Strike: {best_strike.get('strike')} {best_strike.get('option_type', 'CE/PE')}")
    print(f"📉 Strike Delta: {best_strike.get('delta', 'N/A')}")
    print(f"📈 Strike Volume: {best_strike.get('volume', 'N/A')}")
    print(f"💰 Strike LTP: {best_strike.get('lastPrice', 'N/A')}")
else:
    print("⚠️ No strike found matching the required delta (0.59 to 0.69).")
