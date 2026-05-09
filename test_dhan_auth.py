import dhanhq
import os
from dotenv import load_dotenv
load_dotenv()

def test_auth():
    client_id = input("Enter Dhan Client ID: ")
    access_token = input("Enter Dhan Access Token: ")
    
    dhan = dhanhq.dhanhq(client_id, access_token)
    
    print("\nTesting Connection...")
    resp = dhan.get_fund_limits()
    
    if resp.get('status') == 'success':
        print("✅ SUCCESS! Your Dhan API is linked correctly.")
        print(f"Current Fund Limit: {resp.get('data', {}).get('availabelBalance', 'N/A')}")
    else:
        print("❌ FAILED! Authentication Failed.")
        print(f"Remarks: {resp.get('remarks')}")
        print(f"Data: {resp.get('data')}")

if __name__ == "__main__":
    test_auth()
