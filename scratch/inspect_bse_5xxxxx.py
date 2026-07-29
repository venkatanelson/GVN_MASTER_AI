import json

with open("angel_scrip_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

bse_equities = []
for item in data:
    exch = item.get('exch_seg')
    expiry = item.get('expiry')
    inst_type = item.get('instrumenttype')
    token = item.get('token')
    symbol = item.get('symbol')
    
    if exch == 'BSE' and expiry == "" and inst_type == "":
        # Check if token is 6-digit and starts with '5'
        if len(token) == 6 and token.startswith('5'):
            bse_equities.append(item)

print(f"Total BSE items with token starting with '5': {len(bse_equities)}")
print("\nSample BSE equities:")
for item in bse_equities[:30]:
    print(item)
