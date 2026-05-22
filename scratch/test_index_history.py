import sys
import os
import requests
from datetime import datetime

sys.path.append('.')
from nse_option_chain import get_angel_token
import shared_data

token = get_angel_token()
print("Angel Token:", token)

api_key = shared_data.PERMANENT_CREDENTIALS_BACKUP["angel"]["api_key"]

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "127.0.0.1",
    "X-MACAddress": "00:00:00:00:00:00",
    "X-PrivateKey": api_key,
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0"
}

today_str = datetime.now().strftime("%Y-%m-%d")

hist_payload = {
    "exchange": "NSE",
    "symboltoken": "99926000", # Nifty 50 Index
    "interval": "ONE_MINUTE",
    "fromdate": f"{today_str} 09:15",
    "todate": f"{today_str} 09:20"
}

print("Payload:", hist_payload)
url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/v1/getCandleData"
resp = requests.post(url, json=hist_payload, headers=headers, timeout=15)
print("Status:", resp.status_code)
print("Response:", resp.text)
