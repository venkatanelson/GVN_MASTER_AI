import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shared_data

sys.stdout.reconfigure(encoding='utf-8')

def check_connection():
    print("=== BROKER CONNECTION STATUS ===")
    for k, v in shared_data.broker_connection_status.items():
        print(f"{k}: {v}")
        
    print("\n=== PERMANENT CREDENTIALS BACKUP ===")
    print("Angel One Client ID:", shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel", {}).get("client_id"))
    print("Shoonya Client ID:", shared_data.PERMANENT_CREDENTIALS_BACKUP.get("shoonya", {}).get("client_id"))

if __name__ == "__main__":
    check_connection()
