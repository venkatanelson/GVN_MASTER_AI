import requests
import json

def find_nifty_symbols():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    print("Fetching Angel Scrip Master...")
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        print("Searching NIFTY options...")
        count = 0
        for item in data:
            if item.get('exch_seg') == 'NFO' and item.get('name') == 'NIFTY':
                print(f"Symbol: {item.get('symbol')} | Token: {item.get('token')} | Expiry: {item.get('expiry')} | Strike: {item.get('strike')}")
                count += 1
                if count >= 10:
                    break
    else:
        print("Failed to download scrip master")

if __name__ == "__main__":
    find_nifty_symbols()
