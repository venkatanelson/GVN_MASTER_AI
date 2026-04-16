import requests
import json

def test_webhook():
    url = "https://gvn-master-ai.onrender.com/tv-webhook"
    
    # Dummy TradingView Alert Payload
    payload = {
        "symbol": "NIFTY TEST CALL", 
        "transactionType": "BUY",
        "price": 100.00,
        "quantity": 50,
        "target": 120.00,
        "sl": 80.00,
        "status": "Running"
    }

    headers = {'Content-Type': 'application/json'}
    
    print(f"Sending Test Alert to: {url}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        print("\n--- Response from Server ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")

if __name__ == "__main__":
    test_webhook()
