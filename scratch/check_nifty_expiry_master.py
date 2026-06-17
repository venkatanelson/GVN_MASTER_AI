import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

def check_nifty_master():
    print("=== CHECKING NIFTY EXPIRIES IN SCRIP MASTER ===")
    if not os.path.exists("angel_scrip_master.json"):
        print("angel_scrip_master.json does not exist")
        return
        
    with open("angel_scrip_master.json", "r", encoding="utf-8") as f:
        master_data = json.load(f)
        
    nifty_scrips = []
    for item in master_data:
        if item.get('name') == 'NIFTY' and item.get('exch_seg') == 'NFO':
            nifty_scrips.append(item)
            
    print(f"Total NIFTY NFO scrips found: {len(nifty_scrips)}")
    
    # Let's extract unique expiry dates
    expiries = set()
    for s in nifty_scrips:
        expiry = s.get('expiry')
        if expiry:
            expiries.add(expiry)
            
    # Sort them by date
    sorted_exp = sorted(list(expiries), key=lambda x: datetime.strptime(x, "%d%b%Y"))
    print("All NIFTY expiries found:")
    for e in sorted_exp:
        dt = datetime.strptime(e, "%d%b%Y")
        print(f"- {e} ({dt.strftime('%A, %Y-%m-%d')})")

if __name__ == "__main__":
    import os
    check_nifty_master()
