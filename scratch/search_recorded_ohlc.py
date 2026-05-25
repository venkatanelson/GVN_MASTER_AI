import json

with open("gvn_recorded_915_ohlc.json", "r") as f:
    data = json.load(f)

print("=== SEARCHING gvn_recorded_915_ohlc.json ===")
for index, strikes in data.items():
    if isinstance(strikes, dict):
        for strike, val in strikes.items():
            if isinstance(val, dict) and "high" in val and "low" in val:
                h = val["high"]
                l = val["low"]
                # Look for high near 160 or low near 111.6
                if abs(h - 160.0) < 5.0 or abs(l - 111.6) < 5.0:
                    print(f"{index} -> {strike}: High={h}, Low={l}, symbol={val.get('option_symbol')}")
