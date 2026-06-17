import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_history():
    conn = sqlite3.connect("gvn_data_bank.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol, timestamp FROM option_chain_history ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    print("Latest 20 rows in option_chain_history:")
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    check_history()
