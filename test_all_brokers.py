"""
╔══════════════════════════════════════════════════════════════╗
║        GVN MASTER BROKER CONNECTION TESTER                  ║
║   DB lo unna broker details tho anni brokers ki connect     ║
║   Shoonya | Dhan | Zerodha | Fyers | Angel | Upstox        ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python test_all_brokers.py
    
    DB lo unna broker_name chusi automatic ga correct broker
    ki connect avutundi. NorenRestApiPy or any library BYPASS.
"""

import sqlite3
import base64
import hashlib
import json
import requests
import sys
from cryptography.fernet import Fernet

# ─── DB CREDENTIALS LOAD ──────────────────────────────────────
static_key = b'gvn_secure_key_for_encryption_26'
cipher = Fernet(base64.urlsafe_b64encode(static_key))

DB_PATH = 'instance/gvn_algo_pro.db'

def load_broker_config():
    """DB lo unna broker config load cheyyi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                client_id,
                encrypted_access_token,
                encrypted_password,
                encrypted_client_secret,
                encrypted_totp_key,
                broker_name,
                webhook_url,
                encrypted_secret_key
            FROM user_broker_config LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()

        if not row:
            print("❌ DB lo broker config ledu! Dashboard Settings lo credentials enter cheyyandi.")
            sys.exit(1)

        def decrypt(val):
            try:
                return cipher.decrypt(val).decode() if val else ""
            except Exception as e:
                return ""

        config = {
            "client_id":       row[0] or "",
            "access_token":    decrypt(row[1]),   # Dhan/Zerodha/Upstox/Fyers/Angel access token
            "password":        decrypt(row[2]),   # Shoonya / Fyers / Angel password
            "client_secret":   decrypt(row[3]),   # Shoonya api_secret / Zerodha api_secret
            "totp_key":        decrypt(row[4]),   # TOTP Secret Key
            "broker_name":     row[5] or "Dhan",
            "webhook_url":     row[6] or "",
            "tv_secret":       decrypt(row[7]),   # TradingView webhook secret
        }
        return config

    except Exception as e:
        print(f"❌ DB Error: {e}")
        print("   Make sure 'instance/gvn_algo_pro.db' exists and app ran once.")
        sys.exit(1)


def sha256_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_totp(totp_key):
    """TOTP generate cheyyi."""
    if not totp_key:
        return ""
    try:
        import pyotp
        return pyotp.TOTP(totp_key).now()
    except ImportError:
        print("⚠️  pyotp install ledu: pip install pyotp")
        return input("   Manual ga TOTP enter cheyyandi: ").strip()


# ══════════════════════════════════════════════════════════════
#  BROKER 1: SHOONYA (Finvasia) - Direct HTTP Bypass
# ══════════════════════════════════════════════════════════════
def test_shoonya(cfg):
    """
    Shoonya login - Direct HTTP, NorenRestApiPy bypass.
    Fields needed:
      - client_id   = Shoonya User ID (e.g. FA12345)
      - password    = Shoonya Login Password
      - client_secret = API Secret (from Shoonya developer)
      - access_token = Vendor Code (vc)
      - totp_key    = 16-char TOTP Secret
    """
    print("\n" + "═"*55)
    print("🔵  SHOONYA (Finvasia) - Direct HTTP Login Test")
    print("═"*55)

    client_id    = cfg["client_id"]
    vendor_code  = cfg["access_token"]    # access_token field = vendor code for Shoonya
    password     = cfg["password"]
    api_secret   = cfg["client_secret"]
    totp_key     = cfg["totp_key"]

    print(f"📋 Client ID    : {client_id}")
    print(f"📋 Vendor Code  : {vendor_code[:8]}... ({len(vendor_code)} chars)")
    print(f"📋 Password     : {'*'*len(password)} ({len(password)} chars)")
    print(f"📋 API Secret   : {api_secret[:8]}... ({len(api_secret)} chars)")
    print(f"📋 TOTP Key     : {totp_key[:6]}... ({len(totp_key)} chars)")

    if not all([client_id, vendor_code, password, api_secret]):
        print("❌ Missing credentials! Dashboard Settings lo fill cheyyandi:")
        print("   Client ID = Shoonya UserID | Access Token = Vendor Code")
        print("   Client Secret = API Secret | Password = Shoonya Password")
        print("   TOTP = 16-char TOTP Secret")
        return False

    totp = get_totp(totp_key)
    print(f"🔐 TOTP Generated: {totp}")

    pwd_hash     = sha256_hash(password)
    app_key_hash = sha256_hash(f"{api_secret}|{totp}")

    payload = {
        "apkversion": "1.0.0",
        "uid":        client_id,
        "pwd":        pwd_hash,
        "factor2":    totp,
        "vc":         vendor_code,
        "appkey":     app_key_hash,
        "imei":       "abs1234",
        "source":     "API"
    }

    jData = "jData=" + json.dumps(payload)

    try:
        url  = "https://api.shoonya.com/NorenWClientTP/QuickAuth"
        resp = requests.post(url, data=jData, timeout=12)
        print(f"\n📡 HTTP Status : {resp.status_code}")
        print(f"📡 Response    : {resp.text[:300]}")

        result = resp.json()
        if result.get('stat') == 'Ok':
            token = result.get('susertoken', '')
            print(f"\n✅ SHOONYA LOGIN SUCCESS!")
            print(f"   Session Token: {token[:25]}...")
            print(f"   User Name    : {result.get('uname', 'N/A')}")
            return True
        else:
            print(f"\n❌ Shoonya Login Failed: {result.get('emsg', result)}")
            print("👉 Solution: Dashboard Settings → credentials re-enter cheyyandi")
            return False

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  BROKER 2: DHAN - Direct HTTP Bypass
# ══════════════════════════════════════════════════════════════
def test_dhan(cfg):
    """
    Dhan API - Direct HTTP test (no dhanhq library needed).
    Fields needed:
      - client_id   = Dhan Client ID
      - access_token = Dhan Access Token (from developer.dhan.co)
    Note: Dhan doesn't have a login API. Token is a Personal Access Token.
    We verify by calling /fund-limit endpoint.
    """
    print("\n" + "═"*55)
    print("🟠  DHAN (DhanHQ) - Direct HTTP API Test")
    print("═"*55)

    client_id    = cfg["client_id"]
    access_token = cfg["access_token"]

    print(f"📋 Client ID    : {client_id}")
    print(f"📋 Access Token : {access_token[:15]}... ({len(access_token)} chars)")

    if not client_id or not access_token:
        print("❌ Missing! Dashboard Settings lo:")
        print("   Client ID    = Dhan Client ID (numbers)")
        print("   Access Token = Dhan Access Token (developer.dhan.co)")
        return False

    headers = {
        "Accept":        "application/json",
        "Content-Type":  "application/json",
        "access-token":  access_token,
        "client-id":     client_id,
    }

    try:
        # Test 1: Fund Limits (verify auth)
        url  = "https://api.dhan.co/fundlimit"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"\n📡 HTTP Status : {resp.status_code}")
        print(f"📡 Response    : {resp.text[:400]}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"\n✅ DHAN CONNECTION SUCCESS!")
            print(f"   Available Cash : ₹{data.get('availabelBalance', 'N/A')}")
            print(f"   Used Margin    : ₹{data.get('utilizedAmount', 'N/A')}")

            # Test 2: Nifty Spot Price
            print("\n🔄 Fetching Nifty Spot Price from Dhan...")
            mf_url  = "https://api.dhan.co/v2/marketfeed/ltp"
            mf_body = {"IDX_I": ["13"]}  # 13 = NIFTY 50
            mf_resp = requests.post(mf_url, json=mf_body, headers=headers, timeout=10)
            print(f"📊 Nifty LTP Response: {mf_resp.text[:300]}")
            return True

        elif resp.status_code == 401:
            print(f"\n❌ Dhan: Invalid Token (401). Token expired or wrong!")
            print("👉 Solution: developer.dhan.co → Generate new token → Dashboard Settings")
            return False
        else:
            print(f"\n❌ Dhan API Error: {resp.status_code} | {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Dhan Connection Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  BROKER 3: ZERODHA (Kite Connect) - Direct HTTP Bypass
# ══════════════════════════════════════════════════════════════
def test_zerodha(cfg):
    """
    Zerodha Kite Connect - Direct HTTP test.
    Fields needed:
      - client_id    = Zerodha User ID (e.g. AB1234)
      - access_token = Kite Access Token (from kite.trade/connect)
      - client_secret = API Secret (not needed for LTP check, but for auth)
    We verify by calling /user/profile endpoint.
    """
    print("\n" + "═"*55)
    print("🔴  ZERODHA (Kite Connect) - Direct HTTP Test")
    print("═"*55)

    client_id    = cfg["client_id"]
    access_token = cfg["access_token"]
    api_secret   = cfg["client_secret"]

    print(f"📋 User ID      : {client_id}")
    print(f"📋 Access Token : {access_token[:15]}... ({len(access_token)} chars)")

    if not client_id or not access_token:
        print("❌ Missing! Dashboard Settings lo:")
        print("   Client ID    = Zerodha User ID (e.g. AB1234)")
        print("   Access Token = Kite Access Token")
        print("   Client Secret = API Secret (kite.trade/connect)")
        return False

    headers = {
        "Authorization": f"token {client_id}:{access_token}",
        "X-Kite-Version": "3",
    }

    try:
        url  = "https://api.kite.trade/user/profile"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"\n📡 HTTP Status : {resp.status_code}")
        print(f"📡 Response    : {resp.text[:400]}")

        if resp.status_code == 200:
            data = resp.json().get('data', {})
            print(f"\n✅ ZERODHA CONNECTION SUCCESS!")
            print(f"   User Name  : {data.get('user_name', 'N/A')}")
            print(f"   Email      : {data.get('email', 'N/A')}")
            print(f"   Broker     : {data.get('broker', 'N/A')}")

            # Test Nifty LTP
            ltp_url  = "https://api.kite.trade/quote/ltp"
            ltp_resp = requests.get(ltp_url, params={"i": "NSE:NIFTY 50"}, headers=headers, timeout=10)
            ltp_data = ltp_resp.json()
            nifty_ltp = ltp_data.get('data', {}).get('NSE:NIFTY 50', {}).get('last_price', 'N/A')
            print(f"   Nifty LTP  : ₹{nifty_ltp}")
            return True

        elif resp.status_code == 403:
            print(f"\n❌ Zerodha: Token Expired or Invalid (403)")
            print("👉 Solution: kite.trade/connect → Generate new token daily")
            return False
        else:
            print(f"\n❌ Zerodha Error: {resp.status_code} | {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Zerodha Connection Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  BROKER 4: FYERS - Direct HTTP Bypass
# ══════════════════════════════════════════════════════════════
def test_fyers(cfg):
    """
    Fyers API v3 - Direct HTTP test.
    Fields needed:
      - client_id    = App ID (from Fyers dashboard, e.g. ABCDE-100)
      - access_token = Access Token (from fyers.in/api-login)
    We verify via /profile endpoint.
    """
    print("\n" + "═"*55)
    print("🟡  FYERS - Direct HTTP API Test")
    print("═"*55)

    app_id       = cfg["client_id"]
    access_token = cfg["access_token"]

    print(f"📋 App ID       : {app_id}")
    print(f"📋 Access Token : {access_token[:15]}... ({len(access_token)} chars)")

    if not app_id or not access_token:
        print("❌ Missing! Dashboard Settings lo:")
        print("   Client ID    = Fyers App ID (e.g. ABCDE-100)")
        print("   Access Token = Fyers Access Token (fyers.in)")
        return False

    # Fyers token format: "app_id:access_token"
    auth_token = f"{app_id}:{access_token}"
    headers = {
        "Authorization": auth_token,
        "Content-Type":  "application/json",
    }

    try:
        url  = "https://api-t1.fyers.in/api/v3/profile"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"\n📡 HTTP Status : {resp.status_code}")
        print(f"📡 Response    : {resp.text[:400]}")

        if resp.status_code == 200:
            data = resp.json()
            if data.get('s') == 'ok':
                profile = data.get('data', {})
                print(f"\n✅ FYERS CONNECTION SUCCESS!")
                print(f"   Name    : {profile.get('name', 'N/A')}")
                print(f"   FY Code : {profile.get('fy_id', 'N/A')}")
                print(f"   Email   : {profile.get('email_id', 'N/A')}")

                # LTP Test
                ltp_resp = requests.get(
                    "https://api-t1.fyers.in/api/v3/quotes",
                    params={"symbols": "NSE:NIFTY50-INDEX"},
                    headers=headers, timeout=10
                )
                ltp_data = ltp_resp.json()
                nifty_ltp = ltp_data.get('d', [{}])[0].get('v', {}).get('lp', 'N/A') if ltp_data.get('d') else 'N/A'
                print(f"   Nifty LTP: ₹{nifty_ltp}")
                return True
            else:
                print(f"\n❌ Fyers: {data.get('message', 'Unknown error')}")
                return False
        elif resp.status_code == 401:
            print(f"\n❌ Fyers: Token Invalid/Expired!")
            print("👉 Solution: fyers.in → API login → generate new token daily")
            return False
        else:
            print(f"\n❌ Fyers Error: {resp.status_code}")
            return False

    except Exception as e:
        print(f"❌ Fyers Connection Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  BROKER 5: ANGEL ONE (SmartAPI) - Direct HTTP Bypass
# ══════════════════════════════════════════════════════════════
def test_angel(cfg):
    """
    Angel One SmartAPI - Direct HTTP login with TOTP.
    Fields needed:
      - client_id    = Angel One Client Code (XXXXXXX)
      - password     = Angel One MPIN (4-digit)
      - totp_key     = TOTP Secret (from SmartAPI auth app)
      - access_token = API Key (from smartapi.angelbroking.com)
    """
    print("\n" + "═"*55)
    print("🟢  ANGEL ONE (SmartAPI) - Direct HTTP Login Test")
    print("═"*55)

    client_code = cfg["client_id"]
    mpin        = cfg["password"]       # Angel uses 4-digit MPIN
    api_key     = cfg["access_token"]   # access_token field = API Key for Angel
    totp_key    = cfg["totp_key"]

    print(f"📋 Client Code : {client_code}")
    print(f"📋 MPIN        : {'*'*len(mpin)} ({len(mpin)} chars)")
    print(f"📋 API Key     : {api_key[:10]}... ({len(api_key)} chars)")
    print(f"📋 TOTP Key    : {totp_key[:6]}... ({len(totp_key)} chars)")

    if not all([client_code, mpin, api_key]):
        print("❌ Missing! Dashboard Settings lo:")
        print("   Client ID    = Angel One Client Code")
        print("   Password     = Angel One 4-digit MPIN")
        print("   Access Token = SmartAPI API Key")
        print("   TOTP Key     = TOTP Secret (from Angel One auth app)")
        return False

    totp = get_totp(totp_key)
    print(f"🔐 TOTP Generated: {totp}")

    headers = {
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "X-UserType":    "USER",
        "X-SourceID":    "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress":  "00:00:00:00:00:00",
        "X-PrivateKey":  api_key,
    }

    payload = {
        "clientcode": client_code,
        "password":   mpin,
        "totp":       totp,
    }

    try:
        url  = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        print(f"\n📡 HTTP Status : {resp.status_code}")
        print(f"📡 Response    : {resp.text[:400]}")

        data = resp.json()
        if data.get('status') == True and data.get('data'):
            jwt_token = data['data'].get('jwtToken', '')
            print(f"\n✅ ANGEL ONE LOGIN SUCCESS!")
            print(f"   JWT Token  : {jwt_token[:25]}...")
            print(f"   User Name  : {data['data'].get('name', 'N/A')}")
            print(f"   Feed Token : {data['data'].get('feedToken', 'N/A')[:15]}...")
            return True
        else:
            print(f"\n❌ Angel Login Failed: {data.get('message', data)}")
            print("👉 Solution: MPIN, TOTP key, API Key check cheyyandi")
            return False

    except Exception as e:
        print(f"❌ Angel Connection Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  BROKER 6: UPSTOX - Direct HTTP Bypass
# ══════════════════════════════════════════════════════════════
def test_upstox(cfg):
    """
    Upstox API v2 - Direct HTTP test.
    Fields needed:
      - access_token = Upstox Access Token (from upstox.com/openapi)
    Note: Upstox uses OAuth2 - token is generated after browser login.
    We verify via /user/profile endpoint.
    """
    print("\n" + "═"*55)
    print("🟣  UPSTOX - Direct HTTP API Test")
    print("═"*55)

    access_token = cfg["access_token"]

    print(f"📋 Access Token : {access_token[:15]}... ({len(access_token)} chars)")

    if not access_token:
        print("❌ Missing! Dashboard Settings lo:")
        print("   Access Token = Upstox Access Token (upstox.com/openapi)")
        return False

    headers = {
        "Accept":        "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        url  = "https://api.upstox.com/v2/user/profile"
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"\n📡 HTTP Status : {resp.status_code}")
        print(f"📡 Response    : {resp.text[:400]}")

        if resp.status_code == 200:
            data = resp.json().get('data', {})
            print(f"\n✅ UPSTOX CONNECTION SUCCESS!")
            print(f"   Name   : {data.get('user_name', 'N/A')}")
            print(f"   Email  : {data.get('email', 'N/A')}")
            print(f"   Broker : {data.get('broker', 'N/A')}")

            # Nifty LTP
            ltp_resp = requests.get(
                "https://api.upstox.com/v2/market-quote/ltp",
                params={"instrument_key": "NSE_INDEX|Nifty 50"},
                headers=headers, timeout=10
            )
            ltp_data = ltp_resp.json()
            nifty_ltp = ltp_data.get('data', {}).get('NSE_INDEX:Nifty 50', {}).get('last_price', 'N/A')
            print(f"   Nifty LTP: ₹{nifty_ltp}")
            return True

        elif resp.status_code == 401:
            print(f"\n❌ Upstox: Token Expired (401). OAuth token is valid only for 1 day!")
            print("👉 Solution: upstox.com → Login → Generate new Access Token")
            return False
        else:
            print(f"\n❌ Upstox Error: {resp.status_code} | {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Upstox Connection Error: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  MAIN - Auto Detect Broker from DB and Test
# ══════════════════════════════════════════════════════════════
BROKER_TESTS = {
    "shoonya":   test_shoonya,
    "finvasia":  test_shoonya,
    "dhan":      test_dhan,
    "dhanhq":    test_dhan,
    "zerodha":   test_zerodha,
    "kite":      test_zerodha,
    "fyers":     test_fyers,
    "angel":     test_angel,
    "angelone":  test_angel,
    "smartapi":  test_angel,
    "upstox":    test_upstox,
}

if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════╗")
    print("║     GVN MASTER BROKER CONNECTION TESTER         ║")
    print("╚══════════════════════════════════════════════════╝\n")

    cfg = load_broker_config()
    broker = cfg["broker_name"].lower().strip()

    print(f"📌 DB lo broker: '{cfg['broker_name']}'")
    print(f"📌 Client ID   : {cfg['client_id']}")

    # Find matching test function
    test_fn = None
    for key, fn in BROKER_TESTS.items():
        if key in broker:
            test_fn = fn
            break

    if not test_fn:
        print(f"\n⚠️  '{cfg['broker_name']}' broker ki test function ledu!")
        print("   Supported brokers: Shoonya, Dhan, Zerodha, Fyers, Angel, Upstox")
        print("\n📋 Manual broker select cheyyandi:")
        print("   1. Shoonya  2. Dhan  3. Zerodha  4. Fyers  5. Angel  6. Upstox")
        choice = input("   Number select cheyyandi: ").strip()
        fn_map = {
            "1": test_shoonya, "2": test_dhan, "3": test_zerodha,
            "4": test_fyers,   "5": test_angel, "6": test_upstox
        }
        test_fn = fn_map.get(choice)

    if test_fn:
        result = test_fn(cfg)
        print("\n" + "═"*55)
        if result:
            print("🎉  CONNECTION SUCCESSFUL! Broker ki connected!")
            print("    Live trading ready. Dashboard lo Algo ON cheyyandi.")
        else:
            print("❌  CONNECTION FAILED!")
            print("    Dashboard Settings lo credentials check/re-enter cheyyandi.")
        print("═"*55 + "\n")
    else:
        print("❌ No broker selected. Exiting.")
