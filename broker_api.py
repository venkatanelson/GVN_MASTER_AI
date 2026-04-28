import requests
import json
import hashlib
import hmac
import time
import threading
import base64
import pyotp
from dhanhq import dhanhq

# ─── UTILS ──────────────────────────────────────────────────
def sha256_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

def get_totp(totp_key):
    if not totp_key: return ""
    try:
        return pyotp.TOTP(totp_key).now()
    except:
        return ""

# ─── SHOONYA BYPASS ─────────────────────────────────────────
def shoonya_http_login(cfg):
    """Direct HTTP Login for Shoonya (Bypasses NorenRestApiPy)"""
    client_id    = cfg.get("client_id")
    password     = cfg.get("password")
    api_secret   = cfg.get("client_secret")
    vendor_code  = cfg.get("access_token") # access_token field = vendor code
    totp_key     = cfg.get("totp_key")

    if not all([client_id, password, api_secret, vendor_code]):
        return None

    totp = get_totp(totp_key)
    pwd_hash = sha256_hash(password)
    app_key_hash = sha256_hash(f"{api_secret}|{totp}")

    payload = {
        "apkversion": "1.0.0", "uid": client_id, "pwd": pwd_hash,
        "factor2": totp, "vc": vendor_code, "appkey": app_key_hash,
        "imei": "abs1234", "source": "API"
    }
    jData = "jData=" + json.dumps(payload)
    
    url = "https://api.shoonya.com/NorenWClientTP/QuickAuth"
    try:
        resp = requests.post(url, data=jData, timeout=10)
        res = resp.json()
        if res.get('stat') == 'Ok':
            return res.get('susertoken')
    except:
        pass
    return None

# ─── DHAN BYPASS (Direct) ───────────────────────────────────
def dhan_http_test(cfg):
    """Verifies Dhan token and client ID via direct HTTP"""
    headers = {
        "access-token": cfg.get("access_token"),
        "client-id": cfg.get("client_id"),
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get("https://api.dhan.co/fundlimit", headers=headers, timeout=10)
        return resp.status_code == 200
    except:
        return False

# ─── UNIVERSAL ORDER EXECUTION ──────────────────────────────
def place_order_universal(cfg, symbol, txn_type, qty):
    """
    Automatically detects broker and places order using Direct HTTP or Webhook.
    """
    broker = cfg.get("broker_name", "").lower()
    success = False

    # 1. SHOONYA
    if "shoonya" in broker or "finvasia" in broker:
        token = shoonya_http_login(cfg)
        if token:
            # Shoonya Direct Order Placement via HTTP
            url = "https://api.shoonya.com/NorenWClientTP/PlaceOrder"
            payload = {
                "uid": cfg["client_id"], "actid": cfg["client_id"],
                "exch": "NFO", "tsym": symbol, "qty": str(qty),
                "prd": "M", "trantype": txn_type.upper()[0], # B or S
                "prctyp": "MKT", "ret": "DAY"
            }
            jData = "jData=" + json.dumps(payload) + f"&jKey={token}"
            try:
                resp = requests.post(url, data=jData, timeout=10)
                success = resp.json().get('stat') == 'Ok'
            except: pass

    # 2. DHAN (Webhook Priority for Options)
    elif "dhan" in broker:
        if cfg.get("webhook_url") and cfg.get("tv_secret"):
            success = place_dhan_webhook_order(cfg["webhook_url"], cfg["tv_secret"], symbol, txn_type, qty)
        else:
            # Fallback to API if configured
            success = place_dhan_official_api_order(cfg["client_id"], cfg["access_token"], symbol, txn_type, qty)

    # 3. OTHER BROKERS (Generic Webhook)
    else:
        if cfg.get("webhook_url") and cfg.get("tv_secret"):
            success = place_generic_webhook_order(cfg["webhook_url"], cfg["tv_secret"], symbol, txn_type, qty)

    return success

# ─── EXISTING WEBHOOK LOGIC (Optimized) ──────────────────────
def place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    try:
        is_nfo = any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
        clean_symbol = symbol.replace(" ", "").upper()
        payload = {
            "secret": secret_key, "alertType": "single_order",
            "transactionType": "B" if transaction_type.upper() == "BUY" else "S",
            "orderType": "MKT", "quantity": str(quantity),
            "exchange": "NFO" if is_nfo else "NSE", "symbol": clean_symbol,
            "productType": "M", "validity": "DAY", "price": "0"
        }
        resp = requests.post(webhook_url, json=payload, timeout=8)
        return resp.status_code == 200
    except:
        return False

def place_generic_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    try:
        payload = {
            "secret": secret_key, "symbol": symbol, "quantity": quantity,
            "transactionType": transaction_type.upper(), "orderType": "MARKET"
        }
        resp = requests.post(webhook_url, json=payload, timeout=8)
        return resp.status_code == 200
    except:
        return False

def place_dhan_official_api_order(client_id, access_token, symbol, txn_type, qty):
    try:
        dhan = dhanhq(client_id, access_token)
        order = dhan.place_order(
            tag="GVN_ALGO", transaction_type=dhan.BUY if txn_type.upper() == "BUY" else dhan.SELL,
            exchange_segment=dhan.FNO, product_type=dhan.MARGIN, order_type=dhan.MARKET,
            validity=dhan.DAY, security_id=symbol, quantity=int(qty), price=0
        )
        return order.get('status') == 'success'
    except:
        return False

def execute_broker_order_async(cfg, symbol, txn_type, qty, user_name="User"):
    def run_order():
        print(f"🚀 [UNIVERSAL EXECUTION] User: {user_name} | {txn_type} {qty} {symbol}")
        success = place_order_universal(cfg, symbol, txn_type, qty)
        if success:
            print(f"✅ [SUCCESS] Order placed for {user_name}")
        else:
            print(f"❌ [FAILURE] Order failed for {user_name}")

    threading.Thread(target=run_order, daemon=True).start()
