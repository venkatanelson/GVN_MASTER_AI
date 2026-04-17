import sys
import os
from app import app, db, User, UserBrokerConfig, cipher
import requests
import json

def run_test():
    with app.app_context():
        # Find a REAL user with broker config
        user = User.query.filter_by(username='Venkata').first() or User.query.filter_by(user_type='REAL').first()
        if not user:
            print("No REAL user found in database.")
            return
            
        broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
        webhook_url = broker_conf.webhook_url if broker_conf else user.dhan_webhook_url
        enc_secret = broker_conf.encrypted_secret_key if broker_conf else user.encrypted_secret_key
        
        if not webhook_url or not enc_secret:
            print(f"User {user.username} has no Dhan Webhook URL or Secret configured in the database.")
            return
            
        secret_key = cipher.decrypt(enc_secret).decode()
        print(f"Found Configured Webhook URL: {webhook_url}")
        print(f"Found Secret Key: {secret_key[:3]}********")
        
        # Test payload exactly matching Dhan single_order format
        # We will use a dummy symbol so it doesn't accidentally execute a real trade
        payload = {
            "secret": secret_key,
            "transactionType": "B",
            "orderType": "MKT",
            "quantity": "25",
            "exchange": "NFO",
            "symbol": "NIFTY260421C24050",
            "instrument": "OPT",
            "productType": "M",
            "alertType": "multi_leg_order",
            "order_legs": [
                {
                    "transactionType": "B",
                    "orderType": "MKT",
                    "quantity": "25",
                    "exchange": "NFO",
                    "symbol": "NIFTY260421C24050",
                    "instrument": "OPT",
                    "productType": "M"
                }
            ]
        }
        
        print(f"\nSending Payload to Dhan:\n{json.dumps(payload, indent=2)}")
        try:
            resp = requests.post(webhook_url, json=payload, timeout=5)
            print(f"\n--- DHAN BROKER RESPONSE ---")
            print(f"Status Code: {resp.status_code}")
            print(f"Response Text: {resp.text}")
        except Exception as e:
            print(f"HTTP Error while connecting to Dhan: {e}")

if __name__ == '__main__':
    run_test()
