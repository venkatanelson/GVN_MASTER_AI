
import requests
import json

def find_crude_token():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    print("📡 Fetching Angel Scrip Master...")
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        print("🔍 Searching for CRUDEOIL May Futures...")
        for item in data:
            if item['symbol'].startswith('CRUDEOIL') and item['exch_seg'] == 'MCX' and '26MAY' in item['symbol']:
                print(f"✅ Found: {item['symbol']} | Token: {item['token']}")
                return item['token']
    return None

if __name__ == "__main__":
    find_crude_token()
