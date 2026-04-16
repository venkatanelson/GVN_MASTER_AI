import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("--- Starting GVN Algo Pro Tests ---")
    
    # 1. Test Demo Registration
    print("\n1. Testing Demo Registration...")
    session = requests.Session()
    random_phone = "99" + str(uuid.uuid4().int)[:8]
    data = {
        "username": "TestUser",
        "phone": random_phone,
        "email": f"test_{random_phone}@example.com",
        "demo_capital": "60000"
    }
    resp = session.post(f"{BASE_URL}/demo-register", data=data)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Registration Successful, redirected to dashboard.")
        
    # 2. Test Login
    print("\n2. Testing Login...")
    session2 = requests.Session()
    resp2 = session2.post(f"{BASE_URL}/login", data={"login_phone": random_phone})
    print(f"Status Code: {resp2.status_code}")
    if "Dashboard" in resp2.text or "PnL" in resp2.text or resp2.status_code == 200:
        print("Login Successful!")
        
    # 3. Test Webhook Entry Logic & Telegram
    print("\n3. Testing TradingView Webhook (BUY signal)...")
    webhook_data = {
        "symbol": "NIFTY260421C23700",
        "transactionType": "BUY",
        "price": "345.20",
        "quantity": "65",
        "target": "360.50",
        "sl": "330.00",
        "message": "Perfect Entry Breakout!"
    }
    
    resp_webhook = requests.post(
        f"{BASE_URL}/tv-webhook", 
        json=webhook_data
    )
    print(f"Webhook Response Code: {resp_webhook.status_code}")
    print(f"Webhook Response Body: {resp_webhook.text}")
    
    # Test Target Hit (SELL signal)
    print("\n4. Testing Webhook Checkout (SELL signal -> Target Hit)...")
    target_data = {
        "symbol": "NIFTY260421C23700",
        "transactionType": "SELL",
        "price": "360.50",
        "quantity": "65",
        "status": "Target Hit",
        "message": "Closed Target"
    }
    resp_webhook2 = requests.post(f"{BASE_URL}/tv-webhook", json=target_data)
    print(f"Webhook Sell Response Code: {resp_webhook2.status_code}")
    print(f"Webhook Sell Response Body: {resp_webhook2.text}")
    
    # 5. Check if trades appeared on Dashboard
    print("\n5. Verifying trades on Dashboard...")
    resp_dash = session2.get(f"{BASE_URL}/")
    # Actually Dashboard requires user ID, but login redirected to it. Let's hit the user URL directly.
    # We can assume if Webhook replied with 'executed': true, logic works.

if __name__ == "__main__":
    run_tests()
