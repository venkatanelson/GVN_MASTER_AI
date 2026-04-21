import nse_option_chain
import json
import os
from datetime import datetime

print(f"🚀 GVN NSE Engine Test Started at {datetime.now()}")
print("-" * 40)

# Try to fetch data
try:
    print("📡 Fetching NIFTY Option Chain...")
    nse_option_chain.analyze_and_update_gvn_scanner("NIFTY")
    
    last_upd = nse_option_chain.gvn_scanner_data.get("last_updated")
    if last_upd:
        print(f"✅ SUCCESS! Data synced at: {last_upd}")
    else:
        print("❌ FAILED! Data is still empty. Check nse_status.log for errors.")
        
except Exception as e:
    print(f"💥 CRASH! Error during fetch: {e}")

print("-" * 40)
if os.path.exists("nse_status.log"):
    print("📜 Recent Logs (nse_status.log):")
    with open("nse_status.log", "r") as f:
        print("".join(f.readlines()[-5:]))
else:
    print("📝 nse_status.log not found yet.")
