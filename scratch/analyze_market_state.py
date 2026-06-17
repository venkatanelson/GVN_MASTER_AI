import requests
import json
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

sys.stdout.reconfigure(encoding='utf-8')

def analyze():
    port = 8080
    symbols = ["NIFTY", "SENSEX"]
    analysis_results = {}
    
    for sym in symbols:
        url = f"http://127.0.0.1:{port}/api/gvn-scanner?symbol={sym}"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                analysis_results[sym] = r.json()
            else:
                analysis_results[sym] = f"Error: {r.status_code}"
        except Exception as e:
            analysis_results[sym] = f"Connection Failed: {e}"
            
    print(json.dumps(analysis_results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    analyze()
