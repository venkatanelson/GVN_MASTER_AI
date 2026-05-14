import os
import sys
import hashlib
import json

# Path to security_engine_v2.py to get monitored files
SECURITY_FILE = 'security_engine_v2.py'
CRITICAL_FILES = [
    "app.py",
    "nse_option_chain.py",
    "broker_api.py",
    "shared_data.py",
    "security_engine_v2.py",
    "gvn_master_orchestrator.py",
    "truedata_ws_connector.py",
    "gvn_paper_trading_engine.py",
    "gvn_ai_delta60_engine.py"
]

def generate_hash(file_path):
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def reset_hashes():
    print("🛡️ Resetting Security Hashes...")
    new_hashes = {}
    for file in CRITICAL_FILES:
        h = generate_hash(file)
        if h:
            new_hashes[file] = h
            print(f"✅ {file}: {h[:16]}...")

    # Save to a temporary file that security_engine_v2 can read or just update memory
    # Actually, the best way is to trigger the route /admin/authorize-update if the app is running
    import requests
    try:
        r = requests.get("http://127.0.0.1:8080/admin/authorize-update")
        if r.status_code == 200:
            print("🚀 Successfully triggered hash reset via Flask route!")
        else:
            print(f"⚠️ Failed to trigger route: {r.status_code}")
    except Exception as e:
        print(f"❌ App not reachable: {e}. Hashes will be updated on next manual start.")

if __name__ == "__main__":
    reset_hashes()
