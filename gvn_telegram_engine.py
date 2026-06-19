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
        
        import os
        base_api = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org").rstrip('/')
        self.base_url = f"{base_api}/bot{bot_token}"
        self.enabled = bool(bot_token and chat_id)
        
        proxy_url = os.environ.get("TELEGRAM_PROXY")
        self.proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    
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
            resp = requests.post(url, json=payload, proxies=self.proxies, timeout=10)
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
            resp = requests.post(url, files=files, data=data, proxies=self.proxies, timeout=10)
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
    def entry_alert(symbol, entry_price, target, sl, level="NORMAL"):
        """Entry signal alert matching user screenshot format"""
        try: entry_price = round(float(entry_price), 2)
        except: pass
        try: target = round(float(target), 2)
        except: pass
        try: sl = round(float(sl), 2)
        except: pass
        
        return f"""
🚀 GVN MASTER ALGO - NEW ENTRY 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>Symbol:</b> {symbol}
⚡ <b>Level Triggered:</b> {level}
💸 <b>Entry Price:</b> ₹{entry_price}
✅ <b>Target:</b> ₹{target}
⛔ <b>Stop Loss:</b> ₹{sl}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <i>Processed exactly as per GVN Settings</i>
"""
    
    @staticmethod
    def exit_alert(symbol, exit_reason, exit_price, pnl):
        """Exit signal alert matching GVN formatting"""
        try: exit_price = round(float(exit_price), 2)
        except: pass
        try: pnl = round(float(pnl), 2)
        except: pass
        
        status_emoji = "🎯" if "Target" in exit_reason else ("⛔" if "SL" in exit_reason else "⏹️")
        pnl_emoji = "🟩" if float(pnl) > 0 else "🟥"
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
    def wind_alert(symbol, wind_dir, call_pct, put_pct, support, resistance, battle_status, ce_vol, pe_vol, pcr, smart_money, trend_type, is_expiry=False, direction_details=None):
        """Wind Direction and Option Chain DNA Alert"""
        # Determine dominant side emoji
        side_emoji = "🟢" if "UP" in wind_dir or "SHORT" in wind_dir or "SLOW UP" in wind_dir else ("🔴" if "DOWN" in wind_dir or "LONG" in wind_dir or "SLOW DOWN" in wind_dir else "⚖️")
        
        expiry_header = ""
        symbol_str = symbol
        if is_expiry:
            expiry_header = "🚨 <b>EXPIRY SPECIAL STRATEGY ACTIVE</b> 🚨\n"
            symbol_str = f"{symbol} (EXPIRY DAY)"
            
        import shared_data
        active_sym = getattr(shared_data, 'active_dashboard_symbol', 'NIFTY')
        
        algo_mode_str = "📊 DEMO/PAPER"
        try:
            from app import app, User
            with app.app_context():
                user = User.query.filter_by(username="Venkat").first() or User.query.get(1)
                if user:
                    algo_mode_str = "🟢 REAL/LIVE" if (user.user_type == 'LIVE' and user.is_approved) else "📊 DEMO/PAPER"
        except Exception:
            pass

        # Fallback generation for direction details if not provided
        if direction_details is None:
            wind_dir_upper = str(wind_dir).upper()
            direction_val = "UP 🟢" if any(w in wind_dir_upper for w in ["UP", "SHORT", "SLOW UP"]) else ("DOWN 🔴" if any(w in wind_dir_upper for w in ["DOWN", "LONG", "SLOW DOWN"]) else "SIDEWAYS / NEUTRAL 🟡")
            oi_growth_val = "Put Writing (PE) is increasing more 🟢" if "UP" in direction_val else ("Call Writing (CE) is increasing more 🔴" if "DOWN" in direction_val else "Balanced ⚖️")
            strength_val = "Bulls (Put Writers) are gaining strength 💪" if "UP" in direction_val else ("Bears (Call Writers) are gaining strength 💪" if "DOWN" in direction_val else "Balanced / Neutral ⚖️")
            sr_val = "Support is increasing 🟢" if "UP" in direction_val else ("Resistance is increasing 🔴" if "DOWN" in direction_val else "Both Support & Resistance are decreasing ⚖️")
            
            direction_details = {
                "direction": direction_val,
                "oi_growth": oi_growth_val,
                "strength_side": strength_val,
                "sr_movement": sr_val
            }

        return f"""
🌪️ <b>GVN AI WIND & MARKET DNA UPDATE</b> 🌪️
{expiry_header}━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Symbol:</b> {symbol_str}
{side_emoji} <b>Wind Direction:</b> {wind_dir}
⚡ <b>Wind Strength:</b>
  • 🟢 <b>Call Side (Bullish):</b> {call_pct}%
  • 🔴 <b>Put Side (Bearish):</b> {put_pct}%

🛡️ <b>Key Levels (Support & Resistance):</b>
  • 🟢 <b>Support Level:</b> {support}
  • 🔴 <b>Resistance Level:</b> {resistance}

⚔️ <b>Battle Zone Status:</b> {battle_status}
📊 <b>Volume Flow:</b>
  • 🟢 <b>Call Volume:</b> {ce_vol:,}
  • 🔴 <b>Put Volume:</b> {pe_vol:,}
  • ⚖️ <b>PCR (Put-Call Ratio):</b> {pcr:.2f}

🧠 <b>Smart Money Status:</b>
{smart_money}

🧭 <b>Market Direction & Strength (DNA):</b>
  • 🧭 <b>Wind Direction Mode:</b> {direction_details.get('direction')}
  • 📈 <b>OI Growth:</b> {direction_details.get('oi_growth')}
  • 💪 <b>Dominant Strength:</b> {direction_details.get('strength_side')}
  • 🛡️ <b>S/R Movement:</b> {direction_details.get('sr_movement')}

📈 <b>Trend Zone:</b> {trend_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>Algo Mode:</b> {algo_mode_str}
🎯 <b>Trade Symbol:</b> {active_sym} (Trades execute only on this symbol)
━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Sent at: {datetime.now().strftime('%H:%M:%S')}
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
    
    # 🚀 GVN FIX: Class-level throttle to persist across instances
    alert_throttle = {}
    
    def __init__(self, bot_token, chat_id):
        self.bot = TelegramBot(bot_token, chat_id)
        self.alert_history = []
    
    def should_send_alert(self, alert_type, key):
        """Check if alert should be sent (throttle duplicates)"""
        import time
        throttle_key = f"{alert_type}:{key}"
        last_sent = TelegramAlertManager.alert_throttle.get(throttle_key, 0)
        current_time = time.time()
        
        # Allow if > 60 seconds since last identical alert (GVN Standard)
        if current_time - last_sent > 60:
            TelegramAlertManager.alert_throttle[throttle_key] = current_time
            return True
        
        return False
    
    def alert_entry(self, trade_info):
        """Send entry signal"""
        import shared_data
        import os
        import json
        
        trade_sym = trade_info.get("symbol", "")
        
        # Determine the base index symbol from trade_sym
        base_sym = "NIFTY"
        try:
            ts_upper = str(trade_sym).upper()
            if "BANKNIFTY" in ts_upper: base_sym = "BANKNIFTY"
            elif "FINNIFTY" in ts_upper: base_sym = "FINNIFTY"
            elif "MIDCPNIFTY" in ts_upper or "MIDCP" in ts_upper: base_sym = "MIDCPNIFTY"
            elif "SENSEX" in ts_upper: base_sym = "SENSEX"
            elif "MCX" in ts_upper or "CRUDE" in ts_upper: base_sym = "MCX"
            elif "NIFTY" in ts_upper: base_sym = "NIFTY"
        except:
            pass
            
        # Get active dashboard symbol from shared memory
        active_sym = getattr(shared_data, 'active_dashboard_symbol', 'NIFTY')
        
        # Check if today is the expiry day for this symbol
        is_expiry_today = False
        try:
            if hasattr(shared_data, 'expiry_status'):
                is_expiry_today = shared_data.expiry_status.get(base_sym, False)
        except:
            pass
            
        # Bypass active dashboard symbol filter if it is the Expiry Day for this symbol
        if base_sym != active_sym and not is_expiry_today:
            logger.info(f"🔇 [ALERT MUTED] Muted entry alert for {trade_sym} because active dashboard symbol is {active_sym} and it is not expiry day.")
            return
            
        # Verify if it is one of the morning locked strikes for this index
        is_locked = False
        try:
            if os.path.exists("morning_locked_strikes.json"):
                with open("morning_locked_strikes.json", "r") as f:
                    lock_data = json.load(f)
                if lock_data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                    idx_locks = lock_data.get(base_sym, {})
                    ce_lock = idx_locks.get("CE")
                    pe_lock = idx_locks.get("PE")
                    if (ce_lock and str(ce_lock) in trade_sym) or (pe_lock and str(pe_lock) in trade_sym):
                        is_locked = True
        except Exception as e:
            logger.error(f"Error checking morning locked strikes in telegram engine: {e}")
            
        # USER REQUEST: Always send alerts for any active dashboard trade signals, regardless of morning lock
        # if not is_locked:
        #     logger.info(f"🔇 [ALERT MUTED] Muted entry alert for {trade_sym} because it is not a locked morning strike.")
        #     return

        if not self.should_send_alert("ENTRY", trade_sym):
            return
        
        # 🚀 GVN TRANSPARENCY: Print full details to console
        print(f"\n📢 [GVN SIGNAL DETECTED]")
        print(f"🎯 Symbol: {trade_info.get('symbol')}")
        print(f"⚡ Level:  {trade_info.get('level', 'NORMAL')}")
        print(f"💸 Entry:  ₹{trade_info.get('entry_price')}")
        print(f"✅ Target: ₹{trade_info.get('target')}")
        print(f"⛔ SL:     ₹{trade_info.get('sl')}")
        print(f"━━━━━━━━━━━━━━━━━━━━━\n")

        msg = AlertTemplates.entry_alert(
            symbol=trade_info.get("symbol"),
            entry_price=trade_info.get("entry_price"),
            target=trade_info.get("target"),
            sl=trade_info.get("sl"),
            level=trade_info.get("level", "NORMAL")
        )
        
        success = self.bot.send_message(msg)
        if not success:
            print(f"⚠️ [TELEGRAM ERROR] Failed to send entry alert for {trade_info.get('symbol')}")
        
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
    
    def alert_wind(self, symbol, wind_dir, call_pct, put_pct, support, resistance, battle_status, ce_vol, pe_vol, pcr, smart_money, trend_type, is_expiry=False, direction_details=None):
        """Send Wind and Market DNA alert"""
        if not self.should_send_alert("WIND", symbol):
            return
            
        msg = AlertTemplates.wind_alert(
            symbol=symbol,
            wind_dir=wind_dir,
            call_pct=call_pct,
            put_pct=put_pct,
            support=support,
            resistance=resistance,
            battle_status=battle_status,
            ce_vol=ce_vol,
            pe_vol=pe_vol,
            pcr=pcr,
            smart_money=smart_money,
            trend_type=trend_type,
            is_expiry=is_expiry,
            direction_details=direction_details
        )
        
        self.bot.send_message(msg)
        self.alert_history.append({"type": "WIND", "symbol": symbol, "time": datetime.now()})

    
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
    
    def send_direct_message(self, text):
        """Convenience method to send a raw text message directly"""
        return self.bot.send_message(text)

    def get_alert_history(self, limit=10):
        """Get last N alerts"""
        return self.alert_history[-limit:]


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    print("✅ Telegram Alert Engine Initialized")
    if bot_token and chat_id:
        print(f"Testing with Token: {bot_token[:10]}... Chat ID: {chat_id}")
        manager = TelegramAlertManager(bot_token, chat_id)
        
        # Test sending a mock wind alert
        manager.alert_wind(
            symbol="NIFTY",
            wind_dir="🟢 UP WIND (Bullish - PUT Writing)",
            call_pct=80,
            put_pct=20,
            support=23200,
            resistance=23400,
            battle_status="🚀 RESISTANCE BREAKING (Bears Retreating, Bulls Advancing)",
            ce_vol=1250000,
            pe_vol=850000,
            pcr=1.25,
            smart_money="🟢 INSTITUTIONS BUYING (PUT Writing + Positive Delta)",
            trend_type="🔥 Strong Trend (Gamma Explosion Possible)"
        )
        print("Test wind alert sent.")
    else:
        print("⚠️ Bot token or Chat ID missing from environment.")
