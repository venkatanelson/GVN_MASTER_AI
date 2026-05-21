import os
import requests
from dotenv import load_dotenv

load_dotenv()

auth_url = "https://auth.truedata.in/token"
payload = {
    "username": os.getenv("TRUEDATA_USERNAME"),
    "password": os.getenv("TRUEDATA_PASSWORD"),
    "grant_type": "password"
}
response = requests.post(auth_url, data=payload, timeout=30)
token = response.json().get("access_token")
print("Login Status:", response.status_code)
print("Token (first 10 chars):", token[:10] if token else "None")

# Try to query history using gethistory endpoint
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
url = "https://history.truedata.in/api/gethistory"
params = {
    "symbol": "NIFTY 50",
    "from": "260521091500",
    "to": "260521092000",
    "resolution": "1",
    "response": "json"
}

res = requests.get(url, params=params, headers=headers)
print("History Status:", res.status_code)
print("History Response:", res.text)
