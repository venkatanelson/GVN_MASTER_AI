import requests
import json
import hashlib
import hmac
import time
import threading
import base64
import pyotp
import logging
from dhanhq import dhanhq
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BrokerAPI")

# Order tracking
order_history = {
    "total_orders": 0,
    "successful_orders": 0,
    "failed_orders": 0,
    "orders": []
}

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
        logger.warning("Missing Shoonya credentials")
        return None

    totp = get_totp(totp_key)
    pwd_hash = sha256_hash(password)
    # Shoonya QuickAuth requires sha256(uid|api_key)
    app_key_hash = sha256_hash(f"{client_id}|{api_secret}")

    payload = {
        "apkversion": "py:0.0.22", 
        "uid": client_id, 
        "pwd": pwd_hash,
        "factor2": totp, 
        "vc": vendor_code, 
        "appkey": app_key_hash,
        "imei": "abs1234", 
        "source": "API"
    }
    jData = "jData=" + json.dumps(payload)
    
    url = "https://api.shoonya.com/NorenWSTP/QuickAuthenticate"
    try:
        resp = requests.post(url, data=jData, timeout=10)
        res = resp.json()
        if res.get('stat') == 'Ok':
            logger.info("✅ Shoonya login successful")
            return res.get('susertoken')
        else:
            logger.error(f"Shoonya login failed: {res.get('emsg', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Shoonya login exception: {e}")
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
        if resp.status_code == 200:
            logger.info("✅ Dhan authentication successful")
            return True
        else:
            logger.error(f"Dhan auth failed: {resp.status_code}")
    except Exception as e:
        logger.error(f"Dhan test exception: {e}")
    return False

# ─── UNIVERSAL ORDER EXECUTION ──────────────────────────────
def place_order_universal(cfg, symbol, txn_type, qty):
    """
    Automatically detects broker and places order using Direct HTTP or Webhook.
    Returns: Order ID if successful, None if failed
    """
    broker = cfg.get("broker_name", "").lower()
    order_id = None

    logger.info(f"📋 [ORDER] {txn_type} {qty} {symbol} via {broker}")

    # 1. SHOONYA
    if "shoonya" in broker or "finvasia" in broker:
        token = shoonya_http_login(cfg)
        if token:
            order_id = _place_shoonya_order(cfg, token, symbol, txn_type, qty)

    # 2. DHAN (Webhook Priority for Options)
    elif "dhan" in broker:
        if cfg.get("webhook_url") and cfg.get("tv_secret"):
            success = place_dhan_webhook_order(cfg["webhook_url"], cfg["tv_secret"], symbol, txn_type, qty)
            order_id = f"DHAN_WEBHOOK_{int(time.time())}" if success else None
        else:
            # Fallback to API if configured
            order_id = place_dhan_official_api_order(cfg.get("client_id"), cfg.get("access_token"), symbol, txn_type, qty)

    # 3. OTHER BROKERS (Generic Webhook)
    else:
        if cfg.get("webhook_url") and cfg.get("tv_secret"):
            success = place_generic_webhook_order(cfg["webhook_url"], cfg["tv_secret"], symbol, txn_type, qty)
            order_id = f"WEBHOOK_{int(time.time())}" if success else None

    # Track order
    _track_order(order_id, symbol, txn_type, qty, broker)

    return order_id

def _place_shoonya_order(cfg, token, symbol, txn_type, qty):
    """
    Place order directly on Shoonya via HTTP
    """
    try:
        url = "https://api.shoonya.com/NorenWClientTP/PlaceOrder"
        payload = {
            "uid": cfg.get("client_id"), 
            "actid": cfg.get("client_id"),
            "exch": "NFO", 
            "tsym": symbol, 
            "qty": str(qty),
            "prd": "M",  # Margin product
            "trantype": txn_type.upper()[0],  # B or S
            "prctyp": "MKT",  # Market order
            "ret": "DAY"
        }
        jData = "jData=" + json.dumps(payload) + f"&jKey={token}"
        resp = requests.post(url, data=jData, timeout=10)
        res = resp.json()
        
        if res.get('stat') == 'Ok':
            order_id = res.get('norenordno')
            logger.info(f"✅ Shoonya order placed: {order_id}")
            return order_id
        else:
            logger.error(f"Shoonya order failed: {res.get('emsg', 'Unknown error')}")
            return None
    except Exception as e:
        logger.error(f"Shoonya order exception: {e}")
        return None

# ─── EXISTING WEBHOOK LOGIC (Enhanced) ──────────────────────
def place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    """
    Place order via Dhan Webhook (TradingView integration)
    """
    try:
        is_nfo = any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
        clean_symbol = symbol.replace(" ", "").upper()
        payload = {
            "secret": secret_key, 
            "alertType": "single_order",
            "transactionType": "B" if transaction_type.upper() == "BUY" else "S",
            "orderType": "MKT", 
            "quantity": str(quantity),
            "exchange": "NFO" if is_nfo else "NSE", 
            "symbol": clean_symbol,
            "productType": "M", 
            "validity": "DAY", 
            "price": "0"
        }
        resp = requests.post(webhook_url, json=payload, timeout=8)
        success = resp.status_code == 200
        
        if success:
            logger.info(f"✅ Dhan webhook order placed: {clean_symbol}")
        else:
            logger.error(f"Dhan webhook failed: {resp.status_code}")
        
        return success
    except Exception as e:
        logger.error(f"Dhan webhook exception: {e}")
        return False

def place_generic_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    """
    Place order via Generic Webhook
    """
    try:
        payload = {
            "secret": secret_key, 
            "symbol": symbol, 
            "quantity": quantity,
            "transactionType": transaction_type.upper(), 
            "orderType": "MARKET",
            "timestamp": datetime.now().isoformat()
        }
        resp = requests.post(webhook_url, json=payload, timeout=8)
        success = resp.status_code == 200
        
        if success:
            logger.info(f"✅ Generic webhook order placed: {symbol}")
        else:
            logger.error(f"Generic webhook failed: {resp.status_code}")
        
        return success
    except Exception as e:
        logger.error(f"Generic webhook exception: {e}")
        return False

def place_dhan_official_api_order(client_id, access_token, symbol, txn_type, qty):
    """
    Place order via official Dhan API (dhanhq library)
    """
    try:
        dhan = dhanhq(client_id, access_token)
        order = dhan.place_order(
            tag="GVN_ALGO", 
            transaction_type=dhan.BUY if txn_type.upper() == "BUY" else dhan.SELL,
            exchange_segment=dhan.FNO, 
            product_type=dhan.MARGIN, 
            order_type=dhan.MARKET,
            validity=dhan.DAY, 
            security_id=symbol, 
            quantity=int(qty), 
            price=0
        )
        
        if order.get('status') == 'success':
            order_id = order.get('data', {}).get('orderId')
            logger.info(f"✅ Dhan API order placed: {order_id}")
            return order_id
        else:
            logger.error(f"Dhan API order failed: {order.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        logger.error(f"Dhan API exception: {e}")
        return None

def _track_order(order_id, symbol, txn_type, qty, broker):
    """
    Track order in history for analytics
    """
    global order_history
    
    order_history["total_orders"] += 1
    
    if order_id:
        order_history["successful_orders"] += 1
    else:
        order_history["failed_orders"] += 1
    
    order_history["orders"].append({
        "order_id": order_id,
        "symbol": symbol,
        "transaction_type": txn_type,
        "quantity": qty,
        "broker": broker,
        "timestamp": datetime.now().isoformat(),
        "status": "SUCCESS" if order_id else "FAILED"
    })
    
    # Keep last 100 orders
    if len(order_history["orders"]) > 100:
        order_history["orders"].pop(0)

def execute_broker_order_async(cfg, symbol, txn_type, qty, user_name="User"):
    """
    Execute order asynchronously in background thread
    """
    def run_order():
        try:
            logger.info(f"🚀 [ASYNC EXECUTION] User: {user_name} | {txn_type} {qty} {symbol}")
            order_id = place_order_universal(cfg, symbol, txn_type, qty)
            if order_id:
                logger.info(f"✅ [SUCCESS] Order {order_id} placed for {user_name}")
            else:
                logger.error(f"❌ [FAILURE] Order failed for {user_name}")
        except Exception as e:
            logger.error(f"Async order exception: {e}")

    threading.Thread(target=run_order, daemon=True).start()

def get_order_stats():
    """
    Get order execution statistics
    """
    global order_history
    return {
        "total": order_history["total_orders"],
        "successful": order_history["successful_orders"],
        "failed": order_history["failed_orders"],
        "success_rate": (order_history["successful_orders"] / order_history["total_orders"] * 100) if order_history["total_orders"] > 0 else 0
    }
