import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_all_symbols():
    port = 8080
    symbols = ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"]
    for sym in symbols:
        url = f"http://127.0.0.1:{port}/api/gvn-scanner?symbol={sym}"
        print(f"\n--- Testing Symbol: {sym} (URL: {url}) ---")
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                print("Last Updated:", data.get("last_updated"))
                print("Spot Price:", data.get("nifty_spot")) # the endpoint returns nifty_spot as the spot price of the active symbol
                print("Market Pulse for this symbol:", data.get("market_pulse", {}).get(sym, {}))
                print("Z2H Watchlist size:", len(data.get("z2h_watchlist", [])))
                if data.get("z2h_watchlist"):
                    print("Z2H Watchlist:")
                    print(json.dumps(data["z2h_watchlist"], indent=2, ensure_ascii=False))
            else:
                print(f"Error: Status code {r.status_code}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    check_all_symbols()
