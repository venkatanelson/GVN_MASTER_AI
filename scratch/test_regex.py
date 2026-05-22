import json
import re

def main():
    scrip_path = "angel_scrip_master.json"
    with open(scrip_path, "r") as f:
        data = json.load(f)
    
    pattern = re.compile(r"^SENSEX26([0-9OND])([0-9]{2})([0-9]+)(CE|PE)$")
    
    matches = 0
    for item in data:
        exch = item.get('exch_seg')
        name = item.get('name')
        symbol = item.get('symbol', '')
        if exch == 'BFO' and name == 'SENSEX':
            match = pattern.match(symbol)
            if match:
                month_char, day_str, strike_str, opt_type = match.groups()
                print(f"Weekly: {symbol} | Token: {item.get('token')} | MonthChar: {month_char} | Day: {day_str} | Strike: {strike_str} | Expiry: {item.get('expiry')}")
                matches += 1
                if matches >= 20:
                    break

if __name__ == "__main__":
    main()
