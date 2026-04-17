import requests
import threading

def place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity):
    """
    Places an order via Dhan's TradingView Webhook Bridge.
    This logic was extracted from app.py to keep things modular.
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

def execute_broker_order_async(broker_name, webhook_url, secret_key, symbol, transaction_type, quantity, user_name="User"):
    """
    Entry point to run the order in a background thread so the main app doesn't freeze.
    """
    def run_order():
        print(f"🚀 Executing Trade for {user_name} -> Broker: {broker_name} | {transaction_type} {quantity} {symbol}")
        if broker_name.lower() == 'dhan':
            place_dhan_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)
        else:
            place_generic_webhook_order(webhook_url, secret_key, symbol, transaction_type, quantity)

    threading.Thread(target=run_order, daemon=True).start()

# ---------------------------------------------------------
# FUTURE UPGRADE: Official Broker Python APIs (Non-Webhook)
# ---------------------------------------------------------
# If you decide to drop TradingView webhooks and use official DhanHQ python library:
# 
# from dhanhq import dhanhq
# 
# def place_dhan_official_api_order(client_id, access_token, symbol, txn_type, qty):
#     dhan = dhanhq(client_id, access_token)
#     order = dhan.place_order(
#         security_id='1333', # Needs exact security ID for options
#         exchange_segment=dhan.NSE,
#         transaction_type=dhan.BUY if txn_type == "BUY" else dhan.SELL,
#         quantity=qty,
#         order_type=dhan.MARKET,
#         product_type=dhan.MARGIN,
#         price=0
#     )
#     return order
