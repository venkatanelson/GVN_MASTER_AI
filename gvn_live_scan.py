import nse_option_chain as nse
from datetime import datetime
import json

def run_scan():
    print(f"[{datetime.now()}] GVN AI: Fetching Live Alpha Grid Data...")
    try:
        data = nse.fetch_from_nse_direct("NIFTY")
        if not data or "records" not in data:
            print("❌ Error: Could not fetch data from NSE.")
            return

        records = data["records"]["data"]
        spot = data["records"]["underlyingValue"]
        
        # Filter relevant strikes around spot (+/- 300 points)
        relevant_strikes = [s for s in records if abs(s["strikePrice"] - spot) <= 300]
        
        # Sort by Open Interest
        top_oi = sorted(relevant_strikes, key=lambda x: (x.get("CE", {}).get("openInterest", 0) or 0) + (x.get("PE", {}).get("openInterest", 0) or 0), reverse=True)[:7]
        
        print(f"\n--- LIVE NIFTY ALPHA GRID ---")
        print(f"SPOT PRICE: {spot}")
        print(f"{'STRIKE':<10} | {'CALL OI':<12} | {'PUT OI':<12} | {'PCR':<8}")
        print("-" * 50)
        
        total_ce_oi = sum(s.get("CE", {}).get("openInterest", 0) or 0 for s in relevant_strikes)
        total_pe_oi = sum(s.get("PE", {}).get("openInterest", 0) or 0 for s in relevant_strikes)
        overall_pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
        
        for s in top_oi:
            strike = s["strikePrice"]
            ce_oi = s.get("CE", {}).get("openInterest", 0) or 0
            pe_oi = s.get("PE", {}).get("openInterest", 0) or 0
            pcr = round(pe_oi / ce_oi, 2) if ce_oi > 0 else 0
            print(f"{strike:<10} | {ce_oi:<12,} | {pe_oi:<12,} | {pcr:<8}")
            
        print("-" * 50)
        print(f"OVERALL PCR (300 Range): {overall_pcr}")
        
        # Sentiment logic
        sentiment = "NEUTRAL"
        if overall_pcr < 0.7: sentiment = "BEARISH (Strong Resistance)"
        elif overall_pcr > 1.3: sentiment = "BULLISH (Strong Support)"
        print(f"GVN SENTIMENT: {sentiment}")
        
    except Exception as e:
        print(f"❌ Script Error: {str(e)}")

if __name__ == "__main__":
    run_scan()
