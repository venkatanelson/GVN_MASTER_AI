import requests
import json
import pyotp
import time

def test_angel_history():
    client_id = "P218754"
    password = "3061"
    totp_key = "U7IPZ7XFZELCONOX6SHPM4C7I4"
    api_key = "JGYxHp6d"

    totp = pyotp.TOTP(totp_key).now()
    
    # 1. Login to Angel One
    headers = {
        "Content-Type": "application/json", "Accept": "application/json",
        "X-UserType": "USER", "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00", "X-PrivateKey": api_key,
        "User-Agent": "Mozilla/5.0"
    }
    payload = {"clientcode": client_id, "password": password, "totp": totp}
    
    print("Logging in to Angel One...")
    resp = requests.post("https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword", json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"Login failed HTTP {resp.status_code}: {resp.text}")
        return
        
    rj = resp.json()
    if not rj.get('status'):
        print(f"Login response error: {rj}")
        return
        
    jwt = rj.get('data', {}).get('jwtToken')
    print("Login successful! JWT obtained.")

    # 2. Find token for NIFTY26MAY2623600CE in Scrip Master
    print("Fetching Scrip Master...")
    # Using local cache if possible, or downloading
    scrip_resp = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
    if scrip_resp.status_code != 200:
        print("Failed to fetch Scrip Master")
        return
    master_data = scrip_resp.json()
    
    target_symbol = "NIFTY26MAY2623600CE"
    token = None
    for item in master_data:
        if item.get('symbol') == target_symbol and item.get('exch_seg') == 'NFO':
            token = item.get('token')
            print(f"Found token for {target_symbol}: {token}")
            break
            
    if not token:
        print(f"Could not find token for {target_symbol}")
        return

    # 3. Call getCandleData
    headers["Authorization"] = f"Bearer {jwt}"
    hist_payload = {
        "exchange": "NFO",
        "symboltoken": token,
        "interval": "ONE_MINUTE",
        "fromdate": "2026-05-22 09:15",
        "todate": "2026-05-22 09:20"
    }
    
    print(f"Fetching candle data for token {token} ({target_symbol})...")
    hist_resp = requests.post("https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/v1/getCandleData", json=hist_payload, headers=headers)
    print("Status:", hist_resp.status_code)
    print("Response:", json.dumps(hist_resp.json(), indent=2))

if __name__ == "__main__":
    test_angel_history()
