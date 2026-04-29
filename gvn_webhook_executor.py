"""
GVN JSON Webhook Execution Module: Zero-Latency Order Execution
Formats and sends JSON trade signals to brokers for instant execution
"""

import json
import requests
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebhookExecutor")


# ───────────────────────────────────────────────────────────────
# ORDER FORMAT & VALIDATION
# ───────────────────────────────────────────────────────────────

class TradeOrderFormatter:
    """Format trade signals as JSON for broker webhooks"""
    
    @staticmethod
    def format_buy_order(symbol, strike, option_type, quantity, entry_price, target, sl, broker="Dhan"):
        """Format BUY order as JSON"""
        
        order = {
            "secret": "",  # Will be filled from user config
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "quantity": quantity,
            "orderType": "MARKET",
            "price": round(entry_price, 2),
            "transactionType": "BUY",
            "productType": "MARGIN",
            "eventType": "BUY_ACTIVE",
            "timestamp": datetime.now().isoformat(),
            "order_details": {
                "entry": round(entry_price, 2),
                "target": round(target, 2),
                "stoploss": round(sl, 2),
                "risk_points": round(entry_price - sl, 2),
                "reward_points": round(target - entry_price, 2),
                "rr_ratio": round((target - entry_price) / (entry_price - sl), 2) if (entry_price - sl) > 0 else 0
            }
        }
        
        return order
    
    @staticmethod
    def format_sell_order(symbol, strike, option_type, quantity, exit_price, exit_reason="MANUAL", broker="Dhan"):
        """Format SELL order as JSON"""
        
        order = {
            "secret": "",
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "quantity": quantity,
            "orderType": "MARKET",
            "price": round(exit_price, 2),
            "transactionType": "SELL",
            "productType": "MARGIN",
            "exit_reason": exit_reason,
            "status": "Closed",
            "timestamp": datetime.now().isoformat()
        }
        
        return order
    
    @staticmethod
    def validate_order(order: Dict[str, Any]) -> tuple:
        """Validate order format"""
        required_fields = ["symbol", "quantity", "price", "transactionType"]
        
        for field in required_fields:
            if field not in order:
                return False, f"Missing required field: {field}"
        
        if order.get("quantity", 0) <= 0:
            return False, "Quantity must be > 0"
        
        if order.get("price", 0) <= 0:
            return False, "Price must be > 0"
        
        return True, "Valid"


# ───────────────────────────────────────────────────────────────
# WEBHOOK EXECUTOR
# ───────────────────────────────────────────────────────────────

class WebhookExecutor:
    """Send orders to brokers via webhook"""
    
    def __init__(self, webhook_url=None, broker="Dhan"):
        self.webhook_url = webhook_url
        self.broker = broker
        self.execution_log = []
        self.failed_orders = []
    
    def execute_order(self, order: Dict[str, Any], secret_key=None) -> tuple:
        """Execute order via webhook"""
        
        # Validate order
        is_valid, msg = TradeOrderFormatter.validate_order(order)
        if not is_valid:
            logger.error(f"❌ Order validation failed: {msg}")
            return False, msg
        
        # Add secret key if provided
        if secret_key:
            order["secret"] = secret_key
        
        # Check webhook URL
        if not self.webhook_url:
            logger.warning("⚠️ No webhook URL configured - order not executed")
            self.execution_log.append({
                "status": "SIMULATED",
                "order": order,
                "timestamp": datetime.now().isoformat()
            })
            return True, "Simulated (no webhook)"
        
        try:
            # Send JSON to webhook
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GVN-Master-Algo"
            }
            
            response = requests.post(
                self.webhook_url,
                json=order,
                headers=headers,
                timeout=10
            )
            
            # Log execution
            log_entry = {
                "status": "SUCCESS" if response.status_code == 200 else "FAILED",
                "status_code": response.status_code,
                "order": order,
                "response": response.text[:200],
                "timestamp": datetime.now().isoformat()
            }
            
            if response.status_code == 200:
                logger.info(f"✅ Order executed: {order['symbol']} {order['transactionType']}")
                self.execution_log.append(log_entry)
                return True, f"Order executed successfully"
            else:
                logger.error(f"❌ Webhook returned {response.status_code}")
                log_entry["status"] = "FAILED"
                self.execution_log.append(log_entry)
                self.failed_orders.append(log_entry)
                return False, f"Webhook error {response.status_code}"
        
        except requests.exceptions.Timeout:
            logger.error("❌ Webhook timeout")
            return False, "Webhook timeout"
        except requests.exceptions.ConnectionError:
            logger.error("❌ Connection error to webhook")
            return False, "Connection error"
        except Exception as e:
            logger.error(f"❌ Webhook execution error: {e}")
            return False, str(e)
    
    def execute_buy(self, symbol, strike, option_type, quantity, entry_price, target, sl, secret_key=None):
        """Execute BUY order"""
        order = TradeOrderFormatter.format_buy_order(
            symbol, strike, option_type, quantity, entry_price, target, sl, self.broker
        )
        return self.execute_order(order, secret_key)
    
    def execute_sell(self, symbol, strike, option_type, quantity, exit_price, exit_reason, secret_key=None):
        """Execute SELL order"""
        order = TradeOrderFormatter.format_sell_order(
            symbol, strike, option_type, quantity, exit_price, exit_reason, self.broker
        )
        return self.execute_order(order, secret_key)
    
    def get_execution_log(self, limit=20):
        """Get execution history"""
        return self.execution_log[-limit:]
    
    def get_failed_orders(self):
        """Get failed orders for retry"""
        return self.failed_orders
    
    def retry_failed_orders(self, secret_key=None):
        """Retry all failed orders"""
        retried = []
        for failed in self.failed_orders[:]:
            success, msg = self.execute_order(failed["order"], secret_key)
            if success:
                self.failed_orders.remove(failed)
                retried.append(failed["order"])
        
        logger.info(f"🔄 Retried {len(retried)} failed orders")
        return retried


# ───────────────────────────────────────────────────────────────
# DHAN DIRECT API EXECUTOR
# ───────────────────────────────────────────────────────────────

class DhanDirectExecutor:
    """Direct Dhan API execution (bypass webhook)"""
    
    BASE_URL = "https://api.dhan.co"
    
    def __init__(self, access_token, client_id):
        self.access_token = access_token
        self.client_id = client_id
        self.headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }
        self.execution_log = []
    
    def place_order(self, order_data: Dict[str, Any]) -> tuple:
        """Place order directly via Dhan API"""
        
        try:
            url = f"{self.BASE_URL}/order/place"
            
            # Transform GVN order to Dhan format
            dhan_order = {
                "dhanClientId": self.client_id,
                "exchangeTokens": order_data.get("symbol"),
                "quantity": order_data.get("quantity"),
                "price": order_data.get("price"),
                "transactionType": "BUY" if order_data.get("transactionType") == "BUY" else "SELL",
                "orderType": order_data.get("orderType", "MARKET"),
                "productType": order_data.get("productType", "MARGIN")
            }
            
            response = requests.post(
                url,
                json=dhan_order,
                headers=self.headers,
                timeout=10
            )
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "status": "SUCCESS" if response.status_code == 200 else "FAILED",
                "status_code": response.status_code,
                "order": dhan_order,
                "response": response.text[:200]
            }
            self.execution_log.append(log_entry)
            
            if response.status_code == 200:
                resp_json = response.json()
                logger.info(f"✅ Dhan API: Order placed - {resp_json.get('orderId')}")
                return True, resp_json.get("orderId")
            else:
                logger.error(f"❌ Dhan API error: {response.status_code}")
                return False, response.text
        
        except Exception as e:
            logger.error(f"❌ Dhan execution error: {e}")
            return False, str(e)
    
    def cancel_order(self, order_id):
        """Cancel existing order"""
        try:
            url = f"{self.BASE_URL}/order/{order_id}/cancel"
            response = requests.put(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"❌ Cancel failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cancel error: {e}")
            return False


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("✅ Webhook Execution Module Initialized")
    
    # Test order formatting
    buy_order = TradeOrderFormatter.format_buy_order(
        symbol="NIFTY25000CE",
        strike="25000",
        option_type="CE",
        quantity=65,
        entry_price=100,
        target=120,
        sl=80
    )
    
    print("\n📋 Sample BUY Order JSON:")
    print(json.dumps(buy_order, indent=2))
    
    # Test webhook executor (no actual execution without webhook URL)
    executor = WebhookExecutor(webhook_url=None, broker="Dhan")
    success, msg = executor.execute_order(buy_order, secret_key="test_secret")
    print(f"\n📤 Execution Result: {msg}")
