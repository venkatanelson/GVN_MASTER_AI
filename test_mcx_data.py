
import os
from dotenv import load_dotenv
from truedata_rest_api import TrueDataRestAPI
import json

load_dotenv()

def test_mcx():
    user = os.getenv("TRUEDATA_USERNAME")
    pwd = os.getenv("TRUEDATA_PASSWORD")
    
    print(f"🔍 Testing MCX Data for user: {user}...")
    api = TrueDataRestAPI(username=user, password=pwd)
    
    if api.token:
        # Example MCX Symbol for TrueData (Check documentation for exact format)
        # Usually it's like CRUDEOIL24MAYFUT or similar
        # Let's try to get a quote for a common MCX symbol
        symbol = "CRUDEOIL" 
        print(f"📡 Fetching quote for {symbol}...")
        res = api._make_request("getquote", params={"symbol": symbol, "expiry": "19-05-2026"}, service="analytics")
        
        if res:
            print("✅ MCX Data Fetch Successful!")
            print(json.dumps(res, indent=2))
        else:
            print("❌ MCX Data Fetch Failed. Check symbol or permissions.")
    else:
        print("❌ Login Failed.")

if __name__ == "__main__":
    test_mcx()
