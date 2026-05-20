import sys
sys.path.append('.')
from nse_option_chain import fetch_nse_option_chain

res = fetch_nse_option_chain("NIFTY")
if res and "records" in res:
    data = res["records"].get("data", [])
    print("Source:", res.get("source"))
    print("Underlying:", res["records"].get("underlyingValue"))
    for item in data:
        strike = item.get("strikePrice") or item.get("strike")
        ce_lp = item.get("CE", {}).get("lastPrice")
        pe_lp = item.get("PE", {}).get("lastPrice")
        print(f"Strike: {strike} | CE: {ce_lp} | PE: {pe_lp}")
else:
    print("Failed to fetch")
