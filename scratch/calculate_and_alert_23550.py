import os
import json
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

def main():
    # Load .env
    load_dotenv()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "1008887074")
    
    # 1. Calculation Parameters
    high = 271.15
    low = 210.0
    
    diff = high - low
    mid = diff / 2
    n1 = high + mid
    n2 = low + mid
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    # Levels
    i0 = round(gvn0, 2)
    i1 = round(gvn100, 2)
    i2 = round(gvn0 + 0.763 * gvnR, 2)
    i3 = round(gvn0 + 0.618 * gvnR, 2)
    i5 = round(gvn0 + 0.500 * gvnR, 2)
    i6 = round(gvn0 + 0.382 * gvnR, 2)
    i7 = round(gvn0 + 0.220 * gvnR, 2)
    
    # Target & SL (i5 Setup: Target = i1, SL = Entry - 12)
    entry_price = i5
    target_price = i1
    sl_price = round(entry_price - 12, 2)
    
    # Update JSON File (gvn_recorded_915_ohlc.json)
    today_str = datetime.now().strftime("%Y-%m-%d")
    json_path = "gvn_recorded_915_ohlc.json"
    
    data = {}
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            try:
                data = json.load(f)
            except:
                data = {}
                
    data["date"] = today_str
    if "NIFTY" not in data:
        data["NIFTY"] = {}
        
    data["NIFTY"]["23550 CE"] = {
        "high": high,
        "low": low,
        "timestamp": datetime.now().isoformat(),
        "option_symbol": "NIFTY26MAY2623550CE",
        "expiry_date": "2026-05-26",
        "opt_type": "CE"
    }
    
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4)
    print(f"SUCCESS: Updated {json_path} with High={high}, Low={low}")
    
    # Update SQLite database option_915_benchmarks
    db_paths = ["gvn_master.db", "gvn_data_bank.db"]
    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Check table structure or clear cache
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='option_915_benchmarks'")
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE option_915_benchmarks 
                        SET high = ?, low = ?, i1 = ?, i5 = ?, i7 = ?
                        WHERE strike = 23550.0 AND option_type = 'CE' AND date(timestamp) = ?
                    """, (high, low, i1, i5, i7, today_str))
                    
                    if cursor.rowcount == 0:
                        cursor.execute("""
                            INSERT INTO option_915_benchmarks (timestamp, symbol, strike, option_type, high, low, delta, i1, i5, i7)
                            VALUES (?, 'NIFTY', 23550.0, 'CE', ?, ?, 0.65, ?, ?, ?)
                        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), high, low, i1, i5, i7))
                    conn.commit()
                    print(f"SUCCESS: Updated option_915_benchmarks in {db_path}")
                conn.close()
            except Exception as e:
                print(f"WARNING: Error updating DB {db_path}: {e}")
                
    # Prepare Alert Messages
    # Telegram sends Parse HTML, so bold tags work
    # We will send to chat_id, and if it fails, try with -100 prefix just in case it is a supergroup
    chat_ids = [chat_id]
    if not chat_id.startswith("-"):
        chat_ids.append(f"-100{chat_id}")
        
    alert_text = f"""🚀 <b>GVN MASTER ALGO - LEVEL UPDATE</b> 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>Symbol:</b> NIFTY 23550 CE
⚡ <b>Level Type:</b> GVN i5 LEVEL (IPO Entry)
💸 <b>Entry Price (i5):</b> ₹{entry_price}
✅ <b>Target Price (i1):</b> ₹{target_price}
⛔ <b>Stop Loss:</b> ₹{sl_price}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>All Calculated Levels (High: {high}, Low: {low}):</b>
• i1 (Top): ₹{i1}
• i2 (76.3%): ₹{i2}
• i3 (61.8%): ₹{i3}
• i5 (Pivot): ₹{i5}
• i6 (Golden): ₹{i6}
• i7 (Entry): ₹{i7}
• i0 (Bottom): ₹{i0}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <i>Processed exactly as per GVN Settings</i>"""

    print("\nSending Telegram Alerts...")
    for cid in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": cid,
            "text": alert_text,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(url, json=payload, timeout=8)
            print(f"Telegram response for chat_id {cid}: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Telegram error for chat_id {cid}: {e}")

if __name__ == "__main__":
    main()
