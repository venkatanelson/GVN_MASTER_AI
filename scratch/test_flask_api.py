import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_local_server(port):
    url = f"http://127.0.0.1:{port}/api/gvn-scanner"
    print(f"Testing URL: {url}")
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            print(f"Server is running on port {port}!")
            data = r.json()
            print("Z2H Watchlist:")
            print(json.dumps(data.get("z2h_watchlist", []), indent=2, ensure_ascii=False))
            return True
        else:
            print(f"Server returned status code {r.status_code}")
    except Exception as e:
        print(f"Could not connect to server on port {port}: {e}")
    return False

if __name__ == "__main__":
    # Test ports 5000, 8000, 8080, etc.
    for port in [5000, 8000, 8080]:
        if check_local_server(port):
            break
