import requests
import os
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("TELEGRAM_BOT_TOKEN", "8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs")
worker_url = os.environ.get("TELEGRAM_API_URL", "https://rapid-thunder-5a39.nelsonp143.workers.dev")
direct_url = "https://api.telegram.org"

print("--- DIAGNOSING TELEGRAM CONNECTION ---")
print(f"Token: {token[:15]}...")

# 1. Test Direct Telegram connection
print("\n[1] Testing direct connection to api.telegram.org...")
try:
    url = f"{direct_url}/bot{token}/getMe"
    resp = requests.get(url, timeout=5)
    print(f"Direct Response: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Direct Connection Failed: {e}")

# 2. Test Proxy Worker connection
print(f"\n[2] Testing connection via Proxy Worker ({worker_url})...")
try:
    url = f"{worker_url}/bot{token}/getMe"
    resp = requests.get(url, timeout=5)
    print(f"Proxy Response: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"Proxy Connection Failed: {e}")
