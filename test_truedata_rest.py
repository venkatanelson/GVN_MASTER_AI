
import requests
import json

# TrueData REST API Configuration
# Using the token found in the Postman collection
TOKEN = "ii5OnyFFpk7nLmNJcjibxS_6Vt8Cq_YlTmZkcXEyinDsD80_Cj23oXBqgQCrNSRXyl0Otthu3vKQpQQfPenXz68e9RZbbL_TwtfKgMEOdQMfJzLne1FyAtc-g4h_9gw_-X-c9ixDF3gYe0Crq6j6bVToqetFQklYKvH2kNzkwxfOgaX7tS1eTUZq8XsXZdmOmRUnKzHEBvC7UbNcBrnK8TFWuRKLLN1_NjuCpweJOOfKJ_HSjTKLhvB9swUgExHqXdPvFo6Mu1EYREJy_mkurA"
BASE_URL = "https://analytics.truedata.in/api"

def test_option_chain():
    endpoint = f"{BASE_URL}/getoptionchain"
    params = {
        "symbol": "NIFTY",
        "expiry": "28-11-2024" # Example expiry from the collection
    }
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    print(f"Testing TrueData Option Chain API for {params['symbol']}...")
    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Received Data Sample:")
            print(json.dumps(data, indent=2)[:500] + "...")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_option_chain()
