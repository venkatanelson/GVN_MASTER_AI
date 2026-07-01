import json
import os

json_path = "live_market_data.json"

if not os.path.exists(json_path):
    print(f"File not found: {json_path}")
    exit(1)

with open(json_path, "r") as f:
    data = json.load(f)

print("=== KEYS ===")
print(list(data.keys()))

print("\n=== SUMMARY ===")
print(json.dumps(data.get("summary", {}), indent=2))

print("\n=== SCANNER ===")
print(json.dumps(data.get("scanner", {}), indent=2))

print("\n=== PULSE ===")
print(json.dumps(data.get("pulse", {}), indent=2))

print("\n=== LAST UPDATED ===")
print(data.get("last_updated"))
