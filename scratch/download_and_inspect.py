import requests
import json
import os

def main():
    scrip_path = "angel_scrip_master.json"
    if not os.path.exists(scrip_path):
        print("Downloading Scrip Master...")
        resp = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
        if resp.status_code == 200:
            with open(scrip_path, "w") as f:
                f.write(resp.text)
            print("Downloaded and saved.")
        else:
            print("Failed to download:", resp.status_code)
            return
    else:
        print("Scrip Master already exists.")

    print("Loading Scrip Master...")
    with open(scrip_path, "r") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} items.")

    # Let's inspect some symbols matching NIFTY options
    count = 0
    for item in data:
        if item.get('exch_seg') == 'NFO' and 'NIFTY' in item.get('symbol', ''):
            print(f"Symbol: {item.get('symbol')}, Token: {item.get('token')}, Name: {item.get('name')}, Expiry: {item.get('expiry')}, Strike: {item.get('strike')}")
            count += 1
            if count >= 30:
                break

if __name__ == "__main__":
    main()
