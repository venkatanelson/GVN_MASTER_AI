import json
import sys

# Reconfigure stdout to use utf-8 to prevent UnicodeEncodeError in Windows command prompt
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def main():
    try:
        with open("live_market_data.json", "r") as f:
            data = json.load(f)
    except Exception as e:
        print("Error reading json:", e)
        return
        
    nifty_scanner = data.get("scanner", {}).get("NIFTY", [])
    print("=== LIVE NIFTY SCANNER DATA ===")
    for idx, item in enumerate(nifty_scanner):
        strike = item.get('strike')
        ltp = item.get('ltp')
        delta = item.get('delta')
        zone = item.get('zone', 'N/A')
        signal = item.get('ai_signal', 'N/A')
        pressure = item.get('pressure', 'N/A')
        
        # Clean emojis for display just in case
        zone_clean = zone.encode('ascii', errors='ignore').decode('ascii')
        signal_clean = signal.encode('ascii', errors='ignore').decode('ascii')
        pressure_clean = pressure.encode('ascii', errors='ignore').decode('ascii')
        
        print(f"{idx+1}. Strike: {strike}")
        print(f"   LTP: {ltp} | Delta: {delta}")
        print(f"   Zone: {zone_clean.strip()} | Signal: {signal_clean.strip()} | Pressure: {pressure_clean.strip()}")
        levels = item.get("levels", {})
        levels_str = ", ".join([f"{k}: {v}" for k, v in levels.items()])
        print(f"   Levels: {levels_str}")
        print("-" * 50)

if __name__ == "__main__":
    main()
