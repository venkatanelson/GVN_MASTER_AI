import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shared_data
from broker_api import angel_http_login

sys.stdout.reconfigure(encoding='utf-8')

def test_login():
    print("=== TESTING ANGEL ONE LOGIN BY PASSWORD ===")
    cfg = shared_data.PERMANENT_CREDENTIALS_BACKUP["angel"]
    print("Client Code:", cfg["client_id"])
    print("API Key:", cfg["api_key"])
    print("TOTP Key:", cfg["totp_key"])
    
    token = angel_http_login(cfg)
    if token:
        print("✅ SUCCESS! JWT token obtained:", token[:30] + "...")
    else:
        print("❌ FAILED! Could not obtain token.")

if __name__ == "__main__":
    test_login()
