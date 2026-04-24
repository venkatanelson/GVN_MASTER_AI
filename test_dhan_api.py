import os
from dotenv import load_dotenv
load_dotenv()
from cryptography.fernet import Fernet
import base64

# Connect to DB to get Dhan credentials
import sqlite3
import json
from dhanhq import dhanhq

def test_dhan():
    try:
        conn = sqlite3.connect('instance/gvn_algo_pro.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_broker_config LIMIT 1")
        row = cur.fetchone()
        conn.close()
        
        if not row:
            with open("dhan_test_result.json", "w") as f:
                json.dump({"error": "No broker config found"}, f)
            return

        static_32_byte_string = b'gvn_secure_key_for_encryption_26'
        fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
        ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
        cipher = Fernet(ENCRYPTION_KEY)

        client_id = row['client_id']
        enc_token = row['encrypted_access_token']
        access_token = cipher.decrypt(enc_token).decode()
        
        dhan = dhanhq(client_id, access_token)
        
        # Test 1: Option Chain
        oc_resp = dhan.option_chain("13", "IDX_I", "")
        
        # Test 2: Quote Data
        qd_resp = dhan.quote_data({"IDX_I": ["13"]})
        
        # Test 3: Ticker Data
        td_resp = dhan.ticker_data({"IDX_I": ["13"]})
        
        # Test 4: Market Feed Quote
        try:
            mf_resp = dhan.market_feed_quote(instruments=[{"exchange_segment": "IDX_I", "security_id": "13"}])
        except Exception as e:
            mf_resp = str(e)
            
        with open("dhan_test_result.json", "w") as f:
            json.dump({
                "option_chain": oc_resp,
                "quote_data": qd_resp,
                "ticker_data": td_resp,
                "market_feed": mf_resp
            }, f, indent=4)
            
    except Exception as e:
        with open("dhan_test_result.json", "w") as f:
            json.dump({"error": str(e)}, f)

if __name__ == "__main__":
    test_dhan()
