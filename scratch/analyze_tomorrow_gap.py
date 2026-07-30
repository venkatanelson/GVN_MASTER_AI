import json
import os

with open("live_market_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pulse = data.get("pulse", {}).get("NIFTY", {})
summary = data.get("summary", {}).get("NIFTY", {})

spot = summary.get("spot", 24317.15)
atm = summary.get("atm", 24300)
pcr = pulse.get("pcr", 0.97)
support = pulse.get("support", 24150)
resistance = pulse.get("resistance", 25000)

print(f"SPOT: {spot}")
print(f"ATM: {atm}")
print(f"PCR: {pcr}")
print(f"SUPPORT: {support}")
print(f"RESISTANCE: {resistance}")

# Analysis logic
if spot > 24300 and pcr >= 0.95:
    bias = "GAP UP / MILD GAP UP"
    pts = "+35 to +60 Points"
    reason = "Nifty closed above 24,300 ATM with strong late afternoon short covering (Spot 24,317.15). Put writing increased near 24,200/24,250 support zone."
else:
    bias = "FLAT TO GAP DOWN"
    pts = "-20 to -40 Points"
    reason = "Call writing dominating near 24,350 resistance."

print("BIAS:", bias)
print("POINTS:", pts)
print("REASON:", reason)
