import json
import os

scrip_path = "angel_scrip_master.json"
if os.path.exists(scrip_path):
    with open(scrip_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    found = []
    for item in data:
        name = item.get("symbol", "").lower()
        if item.get("exch_seg") == "NSE" and item.get("instrumenttype") == "AMXIDX":
            if "mid" in name or "select" in name:
                found.append(item)
                    
    for item in found:
        print(f"Symbol: {item.get('symbol')} | Name: {item.get('name')} | Token: {item.get('token')} | Exch: {item.get('exch_seg')}")
