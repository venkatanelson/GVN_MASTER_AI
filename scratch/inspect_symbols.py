import json

def main():
    scrip_path = "angel_scrip_master.json"
    with open(scrip_path, "r") as f:
        data = json.load(f)
    
    print("=== NIFTY 23600 & 23750 ===")
    for item in data:
        if item.get('exch_seg') == 'NFO' and item.get('name') == 'NIFTY':
            symbol = item.get('symbol')
            # Check if it contains 23600 or 23750 and CE or PE
            if ('23600' in symbol or '23750' in symbol) and ('CE' in symbol or 'PE' in symbol):
                print(f"NIFTY option: {symbol} | Token: {item.get('token')} | Expiry: {item.get('expiry')}")
                
    print("\n=== BSE/BFO Oct/Nov/Dec Options ===")
    count = 0
    for item in data:
        exch = item.get('exch_seg')
        if exch == 'BFO':
            name = item.get('name')
            symbol = item.get('symbol')
            if name == 'SENSEX':
                # Check for year 26 and check if it has O, N, D or 10, 11, 12 as month
                # Let's print symbols that look like weekly options in late 2026
                # (i.e. length of symbol is longer than monthly)
                # Monthly: SENSEX26OCT... Weekly: SENSEX26O... or SENSEX2610...
                if symbol.startswith('SENSEX26O') or symbol.startswith('SENSEX26N') or symbol.startswith('SENSEX26D') or symbol.startswith('SENSEX2610') or symbol.startswith('SENSEX2611') or symbol.startswith('SENSEX2612'):
                    print(f"Weekly late 2026: {symbol} | Token: {item.get('token')} | Expiry: {item.get('expiry')}")
                    count += 1
                    if count >= 30:
                        break







if __name__ == "__main__":
    main()
