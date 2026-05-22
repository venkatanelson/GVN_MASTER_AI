import json
import os

scrip_path = "angel_scrip_master.json"
if os.path.exists(scrip_path):
    print("Loading file...")
    with open(scrip_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} items.")
    
    # Search for index names
    search_names = ["nifty 50", "nifty bank", "nifty fin", "sensex", "midcap", "bse sensex"]
    found = []
    for item in data:
        name = item.get("symbol", "").lower()
        name_ds = item.get("name", "").lower()
        if item.get("exch_seg") in ["NSE", "BSE"] and item.get("instrumenttype") in ["AMXIDX", "INDEX", ""]:
            for s in search_names:
                if s in name or s in name_ds:
                    found.append(item)
                    break
                    
    print(f"Found {len(found)} candidates:")
    for item in found[:30]:
        print(f"Symbol: {item.get('symbol')} | Name: {item.get('name')} | Token: {item.get('token')} | Exch: {item.get('exch_seg')} | Inst: {item.get('instrumenttype')}")
else:
    print("Scrip master file not found.")
