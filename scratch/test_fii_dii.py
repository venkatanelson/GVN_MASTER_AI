import requests
import pandas as pd
from bs4 import BeautifulSoup
import random
import time
import json
from datetime import datetime

def test_fetch_fii_dii():
    url = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php"
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    
    try:
        print(f"Fetching FII/DII data from Moneycontrol: {url}...")
        response = requests.get(url, headers=headers, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            html = response.text
            print(f"Length of HTML response: {len(html)} characters")
            
            # Check if keywords exist
            for kw in ["FII", "DII", "FII/FPI", "Net Value", "Buy Value"]:
                count = html.upper().count(kw.upper())
                print(f"Keyword '{kw}' occurs {count} times")
            
            # Let's save a snippet of the page text (first 1000 characters and maybe something from the middle)
            soup = BeautifulSoup(response.content, 'html.parser')
            text_snippet = soup.get_text()
            print("\nPage text preview (first 500 chars):")
            # Strip non-ascii characters for printing
            safe_snippet = text_snippet[:500].strip().encode('ascii', errors='ignore').decode('ascii')
            print(safe_snippet)
            
            # Check for Next.js pre-rendered JSON data
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                print("\nSuccess! Found __NEXT_DATA__ script tag.")
                print(f"Data length: {len(next_data.string)} chars")
                
                # Load JSON
                try:
                    js_data = json.loads(next_data.string)
                    # Let's inspect the top-level keys
                    print("Top-level keys in __NEXT_DATA__:")
                    print(list(js_data.keys()))
                    
                    # Usually the page props are under 'props' -> 'pageProps'
                    props = js_data.get("props", {})
                    page_props = props.get("pageProps", {})
                    print("PageProps keys:")
                    print(list(page_props.keys()))
                    
                    # Let's search inside page_props recursively for keys containing "fii" or "dii" or "table"
                    def search_keys(d, path=""):
                        if isinstance(d, dict):
                            for k, v in d.items():
                                if any(x in str(k).lower() for x in ['fii', 'dii', 'activity', 'flow', 'marketstats', 'table']):
                                    # Print key, type, and size/length of value
                                    val_desc = f"Type: {type(v).__name__}"
                                    if isinstance(v, (list, dict)):
                                        val_desc += f", Length: {len(v)}"
                                    elif isinstance(v, (int, float, str)):
                                        val_desc += f", Value: {str(v)[:50]}"
                                    print(f"Found Key: {path}.{k} ({val_desc})")
                                search_keys(v, f"{path}.{k}")
                        elif isinstance(d, list):
                            for idx, item in enumerate(d[:1]): # search first item
                                search_keys(item, f"{path}[{idx}]")
                    
                    search_keys(page_props, "pageProps")
                    
                    # Let's dump a tiny bit of the props to inspect
                    with open("scratch/next_props_debug.json", "w") as f:
                        json.dump(page_props, f, indent=2)
                    print("Dumped pageProps to scratch/next_props_debug.json for debugging.")
                    
                except Exception as ex:
                    print(f"Failed to parse JSON from __NEXT_DATA__: {ex}")
            else:
                print("\n__NEXT_DATA__ script tag NOT found.")
        else:
            print("Failed to fetch page.")
    except Exception as e:
        print(f"Error occurred: {e}")
    return None

if __name__ == "__main__":
    test_fetch_fii_dii()

