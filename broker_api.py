import requests
import threading
from dhanhq import dhanhq

def place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    """
    Places an order via Dhan's TradingView Webhook Bridge.
    """
    try:
        is_nfo = any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
        t_type = "B" if transaction_type.upper() == "BUY" else "S"
        
        payload = {
            "secret": secret_key,
            "alertType": "single_order",
            "transactionType": t_type,
            "orderType": "MKT",
            "quantity": str(quantity),
            "exchange": "NFO" if is_nfo else "NSE",
            "symbol": symbol,
            "instrument": "OPT" if is_nfo else "EQ",
            "productType": "M",
            "price": "0"
        }
        
        resp = requests.post(webhook_url, json=payload, timeout=5)
        print(f"[DHAN WEBHOOK] Symbol: {symbol} | Status: {resp.status_code} | Resp: {resp.text}")
        return resp.status_code == 200
        
    except Exception as e:
        print(f"[DHAN WEBHOOK ERROR] Exception: {str(e)}")
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
        is_nfo = any(idx in symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
        
        # NOTE: Dhan API place_order requires security_id.
        # If 'symbol' passed is numeric, it works. If it's a text symbol, it might fail.
        # But for this implementation, we will try to use it as is.
        order = dhan.place_order(
            tag=symbol,
            transaction_type=dhan.BUY if txn_type.upper() == "BUY" else dhan.SELL,
            exchange_segment=dhan.NFO if is_nfo else dhan.NSE,
            product_type=dhan.MARGIN,
            order_type=dhan.MARKET,
            validity=dhan.DAY,
            security_id=symbol, 
            quantity=int(qty),
            price=0
        )
        print(f"[DHAN API RESP] {order}")
        return order.get('status') == 'success' or order.get('remarks') == 'Order Created'
    except Exception as e:
        print(f"[DHAN API ERROR] {e}")
        return False

def execute_broker_order_async(broker_name, webhook_url, secret_key, symbol, transaction_type, quantity, user_name="User", client_id=None, access_token=None):
    """
    Entry point to run the order in a background thread.
    """
    def run_order():
        print(f"🚀 Executing Trade for {user_name} -> Broker: {broker_name} | {transaction_type} {quantity} {symbol}")
        
        success = False
        if broker_name.lower() == 'dhan' and client_id and access_token:
            success = place_dhan_official_api_order(client_id, access_token, symbol, transaction_type, quantity)
            if not success:
                print("[DHAN] API failed, falling back to Webhook Bridge...")
                success = place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)
        elif broker_name.lower() == 'dhan':
            success = place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)
        else:
            success = place_generic_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)
            
        if success:
            print(f"✅ Trade successful for {user_name}")
        else:
            print(f"❌ Trade FAILED for {user_name}")

    threading.Thread(target=run_order, daemon=True).start()
