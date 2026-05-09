
import os
from truedata_rest_api import TrueDataRestAPI
from dotenv import load_dotenv

load_dotenv()

def check_live_data():
    username = os.getenv("TRUEDATA_USERNAME")
    password = os.getenv("TRUEDATA_PASSWORD")
    port = os.getenv("TRUEDATA_PORT", "8086")

    print(f"📡 Connecting to TrueData for {username}...")
    
    td = TrueDataRestAPI(username, password, port)
    
    if td.login():
        print("✅ TrueData Login Successful!")
        
        # Test MCX Crude Oil (Since Equity is closed)
        # Note: Symbology might vary, trying common MCX formats
        print("\n🔍 Fetching MCX Crude Oil Data...")
        crude_data = td.get_last_quote("CRUDEOIL26MAYFUT") # Example MCX Symbol
        if crude_data:
            print(f"📈 Crude Oil Live: {crude_data}")
        else:
            print("⚠️ Crude Oil FUT not found, checking NIFTY Last Close...")
            nifty = td.get_last_quote("NIFTY 50")
            print(f"📊 NIFTY Last Price: {nifty}")

        # Test Option Chain
        print("\n🔍 Testing Option Chain Fetch...")
        # Trying to fetch NIFTY Option chain (even if closed, it returns last data)
        chain = td.get_option_chain("NIFTY", "2026-05-14") 
        if chain and len(chain) > 0:
            print(f"✅ Option Chain received! Found {len(chain)} strikes.")
            print(f"Example Data: {chain[0]}")
        else:
            print("❌ Option Chain fetch failed or No data available for this expiry.")
            
    else:
        print("❌ TrueData Login Failed. Please check credentials in .env")

if __name__ == "__main__":
    check_live_data()
