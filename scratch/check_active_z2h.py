import urllib.request
import json
import socket

def try_fetch(port):
    url = f"http://127.0.0.1:{port}/api/realtime-data"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                print(f"[+] Success on port {port}!")
                return data
    except Exception as e:
        # print(f"[-] Failed on port {port}: {e}")
        pass
    return None

def main():
    ports = [5000, 8000, 8080, 80]
    data = None
    for port in ports:
        data = try_fetch(port)
        if data:
            break
            
    if not data:
        print("[-] Could not fetch live data from any running web server port. Checking live_market_data.json instead...")
        try:
            with open("live_market_data.json", "r") as f:
                data = json.load(f)
                print("[+] Loaded from live_market_data.json successfully.")
        except Exception as e:
            print(f"[-] Error loading live_market_data.json: {e}")
            return
            
    print("\n=== SYSTEM STATE ===")
    print("NIFTY Spot:", data.get("nifty_spot") or data.get("summary", {}).get("NIFTY", {}).get("spot"))
    
    # Print Z2H Watchlist
    z2h = data.get("z2h_watchlist", [])
    print(f"\n=== Z2H WATCHLIST ({len(z2h)} items) ===")
    if z2h:
        for idx, item in enumerate(z2h, 1):
            print(f"{idx}. {item.get('strike_name')} ({item.get('symbol')})")
            print(f"   LTP: {item.get('ltp')} | 9:15 Low: {item.get('low_915')}")
            print(f"   Levels - i7 (0.220 Fib): {item.get('i7')} | i6 (0.382 Fib): {item.get('i6')} | i5 (0.50 Fib): {item.get('i5')} | Bottom: {item.get('bottom_level')}")
            print(f"   Status: {item.get('status')} | SL: {item.get('sl')} | Entry: {item.get('entry_price')}")
    else:
        print("No active Z2H watchlist items.")

if __name__ == "__main__":
    main()
