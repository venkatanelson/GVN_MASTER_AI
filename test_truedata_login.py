
import os
from dotenv import load_dotenv
from truedata_rest_api import TrueDataRestAPI

load_dotenv()

def test_connection():
    user = os.getenv("TRUEDATA_USERNAME")
    pwd = os.getenv("TRUEDATA_PASSWORD")
    
    print(f"🔍 Testing TrueData connection for user: {user}...")
    api = TrueDataRestAPI(username=user, password=pwd)
    
    if api.token:
        print("✅ Login Successful! Token received.")
        print("🔍 Testing Option Chain fetch...")
        res = api.get_option_chain("NIFTY")
        if res:
            print("✅ Data Fetch Successful! API is working perfectly.")
        else:
            print("❌ Data Fetch Failed. Check API subscription.")
    else:
        print("❌ Login Failed. Check credentials in .env file.")

if __name__ == "__main__":
    test_connection()
