import requests
import threading
from dhanhq import dhanhq

def place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    """
    Places an order via Dhan's TradingView Webhook Bridge.
    """
    try:
        # 🌟 SMART: If secret_key is missing, try to extract it from the URL
        if not secret_key and '/' in webhook_url:
            secret_key = webhook_url.split('/')[-1]
            print(f"[DHAN DEBUG] Extracted Secret Key from URL: {secret_key}")

        is_nfo = any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
        t_type = "B" if transaction_type.upper() == "BUY" else "S"
        
        payload = {
            "secret": secret_key,
            "alertType": "single_order",
            "transactionType": t_type,
            "orderType": "MKT",
            "quantity": str(quantity),
            "exchange": "NFO" if is_nfo else "NSE",
            "symbol": symbol.upper(),
            "productType": "M"
        }
        
        resp = requests.post(webhook_url, json=payload, timeout=8)
        print(f"[DHAN WEBHOOK] URL: {webhook_url[:40]}... | Status: {resp.status_code} | Resp: {resp.text}")
        
        if resp.status_code != 200:
            print(f"❌ [DHAN REJECTION] Broker returned status {resp.status_code}. Check your URL or Secret Key.")
            
        return resp.status_code == 200
        
    except Exception as e:
        print(f"❌ [DHAN WEBHOOK CRITICAL ERROR] {str(e)}")
        return False

def place_generic_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity, price=0.0):
    """
    Fallback for standard webhooks (Upstox, Zerodha 3rd party bridges)
    """
    try:
        payload = {
            "secret": secret_key,
            "symbol": symbol,
            "quantity": quantity,
            "transactionType": transaction_type.upper(),
            "orderType": "MARKET",
            "price": price
        }
        resp = requests.post(webhook_url, json=payload, timeout=5)
        print(f"[GENERIC BROKER] Symbol: {symbol} | Status: {resp.status_code} | Resp: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"[GENERIC BROKER ERROR] Exception: {str(e)}")
        return False

def place_dhan_official_api_order(client_id, access_token, symbol, txn_type, qty):
    """
    Places an order using the official DhanHQ Python SDK.
    """
    try:
        dhan = dhanhq(client_id, access_token)
        # Security IDs for Indices in Dhan
        sec_ids = {"NIFTY": "13", "BANKNIFTY": "25", "FINNIFTY": "27", "SENSEX": "14"}
        sid = sec_ids.get(symbol)
        if not sid:
            print("⚠️ [DHAN API WARNING] Symbol not found in mapped index IDs. Only numeric Security IDs or predefined index keys are supported.")
        
        is_nfo = any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
        
        # NOTE: Dhan API place_order requires security_id.
        # If 'symbol' passed is numeric, it works. If it's a text symbol, it might fail.
        # But for this implementation, we will try to use it as is.
        exchange_const = getattr(dhan, 'FNO', 'FNO')
        order = dhan.place_order(
            tag=symbol[:20],  # Dhan tag limits to 20 chars
            transaction_type=dhan.BUY if txn_type.upper() == "BUY" else dhan.SELL,
            exchange_segment=exchange_const if is_nfo else dhan.NSE,
            product_type=dhan.MARGIN,
            order_type=dhan.MARKET,
            validity=dhan.DAY,
            security_id=symbol, 
            quantity=int(qty),
            price=0
        )
        print(f"[DHAN API RESP] {order}")
        if order.get('status') == 'failure':
            print(f"❌ [DHAN API REJECTION] Reason: {order.get('remarks')}")
            if "security_id" in str(order.get('remarks', '')).lower():
                print("💡 TIP: The Dhan Official API requires a numeric Security ID (e.g., '12345'). It cannot process string symbols like 'NIFTY 25 APR 19500 CE' directly.")
        return order.get('status') == 'success' or order.get('remarks') == 'Order Created'
    except Exception as e:
        if "DH-905" in str(e) or "Invalid IP" in str(e):
            print("⚠️ [DHAN API ALERT] Your API Key is restricted by IP. Please go to Dhan Developer Portal and set 'Access IP' to 'Any' (0.0.0.0/0).")
        print(f"[DHAN API ERROR] {e}")
        return False

def execute_broker_order_async(broker_name, webhook_url, secret_key, symbol, transaction_type, quantity, user_name="User", client_id=None, access_token=None):
    """
    Entry point to run the order in a background thread.
    """
    def run_order():
        print(f"🚀 Executing Trade for {user_name} -> Broker: {broker_name} | {transaction_type} {quantity} {symbol}")
        
        success = False
        if broker_name.lower() == 'dhan':
            # Priority 1: Official Dhan API (Gives instant Pass/Fail & Rejection reasons)
            if client_id and access_token:
                print(f"[DHAN] Using Official API for {symbol}...")
                success = place_dhan_official_api_order(client_id, access_token, symbol, transaction_type, quantity)
            
            # Priority 2: Fallback to Webhook Bridge if API fails or credentials are missing
            if not success and webhook_url and secret_key:
                print(f"[DHAN] Falling back to Webhook Bridge for {symbol}...")
                success = place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)
        else:
            success = place_generic_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)
            
        if success:
            print(f"✅ Trade successful for {user_name}")
        else:
            print(f"❌ Trade FAILED for {user_name}")

    threading.Thread(target=run_order, daemon=True).start()
def force_square_off_all_positions(client_id, access_token):
    """
    Fetches all open positions and squares them off immediately.
    """
    try:
        dhan = dhanhq(client_id, access_token)
        positions_resp = dhan.get_positions()
        
        if positions_resp.get('status') == 'success':
            positions = positions_resp.get('data', [])
            closed_count = 0
            for pos in positions:
                net_qty = int(pos.get('netQty', 0))
                if net_qty != 0:
                    # Square off by placing opposite order
                    security_id = pos.get('securityId')
                    exchange = pos.get('exchangeSegment')
                    product = pos.get('productType')
                    
                    txn_type = dhan.SELL if net_qty > 0 else dhan.BUY
                    qty = abs(net_qty)
                    
                    dhan.place_order(
                        tag="ADMIN_FORCE_EXIT",
                        transaction_type=txn_type,
                        exchange_segment=exchange,
                        product_type=product,
                        order_type=dhan.MARKET,
                        validity=dhan.DAY,
                        security_id=security_id,
                        quantity=qty,
                        price=0
                    )
                    closed_count += 1
            print(f"🛑 [ADMIN] Force Closed {closed_count} positions for client {client_id}")
            return True
        else:
            print(f"⚠️ No active positions to close for client {client_id}")
            return True
    except Exception as e:
        print(f"❌ [FORCE SQUARE OFF ERROR] {e}")
        return False

def get_dhan_ltp(client_id, access_token, security_id, exchange_segment="NSE_FNO"):
    """
    Fetches real-time LTP from Dhan HQ for a specific security ID.
    Note: security_id must be numeric.
    """
    try:
        dhan = dhanhq(client_id, access_token)
        # exchange_segment mapping
        seg = dhan.FNO if "FNO" in exchange_segment.upper() else dhan.NSE
        
        quote = dhan.get_quote(security_id, seg)
        if quote.get('status') == 'success':
            return float(quote.get('data', {}).get('lastTradedPrice', 0.0))
        return 0.0
    except Exception as e:
        print(f"❌ [DHAN LTP ERROR] {e}")
        return 0.0
