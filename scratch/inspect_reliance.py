import json

with open("angel_scrip_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

reliances = [item for item in data if item.get('name') == 'RELIANCE' and item.get('exch_seg') in ['NSE', 'BSE']]
print(f"Found {len(reliances)} entries for RELIANCE in NSE/BSE:")
for item in reliances:
    print(item)
