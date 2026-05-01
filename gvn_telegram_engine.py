"""
GVN Telegram Alert Engine: Instant Notifications for Entry/Exit/Status
Sends real-time trade signals and system status to private Telegram channel
"""

import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramEngine")


# ───────────────────────────────────────────────────────────────
# TELEGRAM BOT CONFIGURATION
# ───────────────────────────────────────────────────────────────

class TelegramBot:
    """Telegram API wrapper for GVN alerts"""
    
    def __init__(self, bot_token, chat_id):
        """
        Initialize Telegram bot
        bot_token: From @BotFather
        chat_id: Private channel ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token and chat_id)
    
    def send_message(self, text):
        """Send plain text message"""
        if not self.enabled:
            logger.warning("⚠️ Telegram not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                logger.info(f"✅ Telegram: {text[:50]}...")
                return True
            else:
                logger.error(f"Telegram send failed: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def send_document(self, file_content, filename, caption=""):
        """Send document/file"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendDocument"
            files = {'document': (filename, file_content)}
            data = {'chat_id': self.chat_id, 'caption': caption}
            resp = requests.post(url, files=files, data=data, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Document send error: {e}")
            return False


# ───────────────────────────────────────────────────────────────
# ALERT MESSAGE TEMPLATES
# ───────────────────────────────────────────────────────────────

class AlertTemplates:
    """Pre-formatted alert messages"""
    
    @staticmethod
    def entry_alert(symbol, entry_price, target, sl):
        """Entry signal alert matching user screenshot format"""
        return f"""
🚀 GVN MASTER ALGO - NEW ENTRY 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>Symbol:</b> {symbol}
💸 <b>Entry Price:</b> ₹{entry_price}
✅ <b>Target:</b> ₹{target}
⛔ <b>Stop Loss:</b> ₹{sl}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <i>Processed exactly as per GVN Settings</i>
"""
    
    @staticmethod
    def exit_alert(symbol, exit_reason, exit_price, pnl):
        """Exit signal alert matching GVN formatting"""
        status_emoji = "🎯" if "Target" in exit_reason else ("⛔" if "SL" in exit_reason else "⏹️")
        pnl_emoji = "🟩" if pnl > 0 else "🟥"
        return f"""
{status_emoji} GVN MASTER ALGO - TRADE CLOSED {status_emoji}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Symbol:</b> {symbol}
🔔 <b>Reason:</b> {exit_reason}
💸 <b>Exit Price:</b> ₹{exit_price}
{pnl_emoji} <b>P&L:</b> ₹{pnl}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <i>Processed exactly as per GVN Settings</i>
"""
    
    @staticmethod
    def sentiment_alert(verdict, score, session, momentum_desc, pcr):
        """Market sentiment alert"""
        return f"""
📊 <b>MARKET SENTIMENT UPDATE</b>
━━━━━━━━━━━━━━━━━
<b>Verdict:</b> {verdict}
<b>Score:</b> {score}/5
<b>Session:</b> {session}
<b>Momentum:</b> {momentum_desc}
<b>PCR:</b> {pcr}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
    
    @staticmethod
    def system_status_alert(status, message):
        """System status alert"""
        if status == "CONNECTED":
            icon = "🟢"
        elif status == "DISCONNECTED":
            icon = "🔴"
        else:
            icon = "🟡"
        
        return f"""
{icon} <b>SYSTEM STATUS: {status}</b>
━━━━━━━━━━━━━━━━━
<b>Message:</b> {message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
    
    @staticmethod
    def daily_summary(total_trades, winning_trades, losing_trades, total_pnl):
        """End-of-day summary"""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        status = "📈 PROFIT DAY" if total_pnl > 0 else "📉 LOSS DAY"
        
        return f"""
{status}
━━━━━━━━━━━━━━━━━
<b>Total Trades:</b> {total_trades}
<b>Winning:</b> {winning_trades} ({win_rate:.1f}%)
<b>Losing:</b> {losing_trades}
<b>Total P&L:</b> {total_pnl} pts

🔐 <i>Auto Square-off at 3:15 PM Triggered</i>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


# ───────────────────────────────────────────────────────────────
# TELEGRAM ALERT MANAGER
# ───────────────────────────────────────────────────────────────

class TelegramAlertManager:
    """Centralized alert dispatch system"""
    
    def __init__(self, bot_token, chat_id):
        self.bot = TelegramBot(bot_token, chat_id)
        self.alert_history = []
        self.alert_throttle = {}  # Prevent duplicate alerts
    
    def should_send_alert(self, alert_type, key):
        """Check if alert should be sent (throttle duplicates)"""
        import time
        throttle_key = f"{alert_type}:{key}"
        last_sent = self.alert_throttle.get(throttle_key, 0)
        current_time = time.time()
        
        # Allow if > 30 seconds since last identical alert
        if current_time - last_sent > 30:
            self.alert_throttle[throttle_key] = current_time
            return True
        
        return False
    
    def alert_entry(self, trade_info):
        """Send entry signal"""
        if not self.should_send_alert("ENTRY", trade_info.get("symbol")):
            return
        
        msg = AlertTemplates.entry_alert(
            symbol=trade_info.get("symbol"),
            entry_price=trade_info.get("entry_price"),
            target=trade_info.get("target"),
            sl=trade_info.get("sl")
        )
        
        self.bot.send_message(msg)
        self.alert_history.append({"type": "ENTRY", "data": trade_info, "time": datetime.now()})
    
    def alert_exit(self, trade_info):
        """Send exit signal"""
        key = f"{trade_info.get('symbol')}:{trade_info.get('exit_reason')}"
        if not self.should_send_alert("EXIT", key):
            return
        
        msg = AlertTemplates.exit_alert(
            symbol=trade_info.get("symbol"),
            exit_reason=trade_info.get("exit_reason"),
            exit_price=trade_info.get("exit_price"),
            pnl=trade_info.get("pnl", 0)
        )
        
        self.bot.send_message(msg)
        self.alert_history.append({"type": "EXIT", "data": trade_info, "time": datetime.now()})
    
    def alert_sentiment(self, sentiment_analysis):
        """Send market sentiment"""
        if not self.should_send_alert("SENTIMENT", "market"):
            return
        
        msg = AlertTemplates.sentiment_alert(
            verdict=sentiment_analysis.get("verdict"),
            score=sentiment_analysis.get("score"),
            session=sentiment_analysis.get("components", {}).get("session"),
            momentum_desc=sentiment_analysis.get("components", {}).get("momentum_desc"),
            pcr=sentiment_analysis.get("components", {}).get("pcr")
        )
        
        self.bot.send_message(msg)
        self.alert_history.append({"type": "SENTIMENT", "data": sentiment_analysis, "time": datetime.now()})
    
    def alert_status(self, status, message):
        """Send system status"""
        msg = AlertTemplates.system_status_alert(status, message)
        self.bot.send_message(msg)
        self.alert_history.append({"type": "STATUS", "status": status, "message": message, "time": datetime.now()})
    
    def alert_daily_summary(self, summary):
        """Send end-of-day summary"""
        msg = AlertTemplates.daily_summary(
            total_trades=summary.get("total_trades", 0),
            winning_trades=summary.get("winning_trades", 0),
            losing_trades=summary.get("losing_trades", 0),
            total_pnl=summary.get("total_pnl", 0)
        )
        
        self.bot.send_message(msg)
        self.alert_history.append({"type": "SUMMARY", "data": summary, "time": datetime.now()})
    
    def get_alert_history(self, limit=10):
        """Get last N alerts"""
        return self.alert_history[-limit:]


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # This would need actual bot token and chat ID to test
    # manager = TelegramAlertManager("YOUR_BOT_TOKEN", "YOUR_CHAT_ID")
    
    # Test templates
    print("✅ Telegram Alert Engine Initialized")
    print("\n📋 Entry Alert Sample:")
    print(AlertTemplates.entry_alert(
        symbol="NIFTY260421C24100",
        entry_price=292.0,
        target=354.39,
        sl=276.63
    ))
