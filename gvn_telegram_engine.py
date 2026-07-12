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
        """Entry signal alert - Short & Sweet Version"""
        try: entry_price = round(float(entry_price), 2)
        except: pass
        try: target = round(float(target), 2)
        except: pass
        try: sl = round(float(sl), 2)
        except: pass
        
        is_z2h = "Z2H" in str(level).upper() or "ZERO" in str(level).upper()
        clean_sym = str(symbol).replace("_", "").replace(" ", "").upper()
        execution_cmd = f"BUY {clean_sym} ENTRY {entry_price} SL {sl} TGT {target}"
        
        if is_z2h:
            return f"""🚀 <b>GVN ZERO-TO-HERO BLAST</b> 🚀
━━━━━━━━━━━━━━━━━━
🎯 <b>Strike:</b> {symbol}
🟢 <b>Entry Zone (i1):</b> ₹{entry_price}
🎯 <b>Target:</b> ₹{target}
⛔ <b>Stop Loss:</b> ₹{sl}
🌪️ <i>Z2H Wind Sync: ACTIVE</i>
━━━━━━━━━━━━━━━━━━
🤖 <b>ANGEL ONE EXECUTION:</b>
<code>{execution_cmd}</code>
"""
        else:
            return f"""⚡ <b>GVN DUAL-SYNC BUY</b> ⚡
━━━━━━━━━━━━━━━━━━
🎯 <b>Strike:</b> {symbol}
🟢 <b>Trigger:</b> {level}
💸 <b>Entry LTP:</b> ₹{entry_price}
🎯 <b>Target:</b> ₹{target}
⛔ <b>Stop Loss:</b> ₹{sl}
━━━━━━━━━━━━━━━━━━
🤖 <b>ANGEL ONE EXECUTION:</b>
<code>{execution_cmd}</code>
"""
    
    @staticmethod
    def exit_alert(symbol, exit_reason, exit_price, pnl):
        """Exit signal alert - Short & Sweet Version"""
        try: exit_price = round(float(exit_price), 2)
        except: pass
        try: pnl = round(float(pnl), 2)
        except: pass
        
        status_emoji = "🎯" if "Target" in exit_reason else ("⛔" if "SL" in exit_reason else "⏹️")
        pnl_emoji = "🟩" if float(pnl) > 0 else "🟥"
        clean_sym = str(symbol).replace("_", "").replace(" ", "").upper()
        execution_cmd = f"SELL {clean_sym} EXIT {exit_price}"
        
        return f"""{status_emoji} <b>GVN TRADE CLOSED</b> {status_emoji}
━━━━━━━━━━━━━━━━━━
🎯 <b>Strike:</b> {symbol}
🔔 <b>Reason:</b> {exit_reason}
💸 <b>Exit Price:</b> ₹{exit_price}
{pnl_emoji} <b>P&L:</b> {pnl} pts
━━━━━━━━━━━━━━━━━━
🤖 <b>ANGEL ONE EXECUTION:</b>
<code>{execution_cmd}</code>
"""
    
    @staticmethod
    def sentiment_alert(verdict, score, session, momentum_desc, pcr):
        """Market sentiment alert"""
        return f"""📊 <b>MARKET SENTIMENT UPDATE</b>
━━━━━━━━━━━━━━━━━
<b>Verdict:</b> {verdict}
<b>Score:</b> {score}/5
<b>Session:</b> {session}
<b>Momentum:</b> {momentum_desc}
<b>PCR:</b> {pcr}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
    
    @staticmethod
    def wind_alert(symbol, wind_dir, call_pct, put_pct, support, resistance, battle_status, ce_vol, pe_vol, pcr, smart_money, trend_type, is_expiry=False, direction_details=None,
                   max_ce_oi_strike=0, max_pe_oi_strike=0, max_ce_oi_val=0, max_pe_oi_val=0,
                   max_ce_oi_pct_strike=0, max_pe_oi_pct_strike=0, max_ce_oi_pct_val=0.0, max_pe_oi_pct_val=0.0,
                   nifty_rsi=50.0, rsi_confirm_msg="", participant_data=None):
        """Wind Direction and Option Chain DNA Alert - Detailed Version"""
        # Determine dominant side emoji
        side_emoji = "🟢" if "UP" in str(wind_dir).upper() or "SHORT" in str(wind_dir).upper() or "SLOW UP" in str(wind_dir).upper() else ("🔴" if "DOWN" in str(wind_dir).upper() or "LONG" in str(wind_dir).upper() or "SLOW DOWN" in str(wind_dir).upper() else "⚖️")
        
        expiry_str = " (EXPIRY DAY)" if is_expiry else ""
        
        # Participant OI Analysis Formatting
        part_str = ""
        verdict_str = ""
        if participant_data:
            try:
                client_opt_net = participant_data["client_idx_call_long"] - participant_data["client_idx_call_short"] + participant_data["client_idx_put_short"] - participant_data["client_idx_put_long"]
                fii_opt_net = participant_data["fii_idx_call_long"] - participant_data["fii_idx_call_short"] + participant_data["fii_idx_put_short"] - participant_data["fii_idx_put_long"]
                pro_opt_net = participant_data["pro_idx_call_long"] - participant_data["pro_idx_call_short"] + participant_data["pro_idx_put_short"] - participant_data["pro_idx_put_long"]
                dii_opt_net = participant_data["dii_idx_call_long"] - participant_data["dii_idx_call_short"] + participant_data["dii_idx_put_short"] - participant_data["dii_idx_put_long"]
                
                client_fut_net = participant_data["client_idx_fut_long"] - participant_data["client_idx_fut_short"]
                fii_fut_net = participant_data["fii_idx_fut_long"] - participant_data["fii_idx_fut_short"]
                pro_fut_net = participant_data["pro_idx_fut_long"] - participant_data["pro_idx_fut_short"]
                dii_fut_net = participant_data["dii_idx_fut_long"] - participant_data["dii_idx_fut_short"]
                
                emoji_fn = lambda val: "🟢 (BULL)" if val > 10000 else ("🔴 (BEAR)" if val < -10000 else "⚖️ (NEUTRAL)")
                
                part_str = f"""
👥 <b>Participant OI Positions:</b>
• 🏢 <b>FIIs:</b> {emoji_fn(fii_opt_net)} Opt: {fii_opt_net/1000.0:+.1f}k | Fut: {fii_fut_net/1000.0:+.1f}k
• 👔 <b>PROs:</b> {emoji_fn(pro_opt_net)} Opt: {pro_opt_net/1000.0:+.1f}k | Fut: {pro_fut_net/1000.0:+.1f}k
• 👥 <b>Clients:</b> {emoji_fn(client_opt_net)} Opt: {client_opt_net/1000.0:+.1f}k | Fut: {client_fut_net/1000.0:+.1f}k
• 🏛️ <b>DIIs:</b> {emoji_fn(dii_opt_net)} Opt: {dii_opt_net/1000.0:+.1f}k | Fut: {dii_fut_net/1000.0:+.1f}k
"""
                # Calculate verdict
                verdict = "NEUTRAL ⚖️"
                if fii_opt_net < -10000 or (abs(fii_opt_net) <= 10000 and pro_opt_net < -10000):
                    verdict = "BEARISH 🔴"
                elif fii_opt_net > 10000 or (abs(fii_opt_net) <= 10000 and pro_opt_net > 10000):
                    verdict = "BULLISH 🟢"
                
                verdict_str = f"🎯 <b>Institutional Verdict:</b> {verdict}\n"
            except Exception as e:
                part_str = f"\n⚠️ Error parsing participant data: {e}"
        
        return f"""🌪️ <b>GVN AI WIND & TREND DNA</b> 🌪️
━━━━━━━━━━━━━━━━━━
📊 <b>{symbol}{expiry_str}</b>
⚖️ <b>Wind Direction:</b> {side_emoji} {wind_dir}
💪 <b>Strength:</b> 🟢 CE {call_pct}% | 🔴 PE {put_pct}%
📈 <b>Trend Zone:</b> {trend_type}
🛡️ <b>Levels:</b> Supp: {support} | Res: {resistance}
{verdict_str}
🧱 <b>Option Chain Walls:</b>
• <b>Biggest OI:</b>
  - 🟢 PE Support: {max_pe_oi_strike} ({max_pe_oi_val/100000.0:.2f}L)
  - 🔴 CE Resistance: {max_ce_oi_strike} ({max_ce_oi_val/100000.0:.2f}L)
• <b>Strongest Build-up:</b>
  - 🟢 PE Support: {max_pe_oi_pct_strike} (+{max_pe_oi_pct_val:.1f}%)
  - 🔴 CE Resistance: {max_ce_oi_pct_strike} (+{max_ce_oi_pct_val:.1f}%)

📈 <b>RSI-50 Validation:</b>
• {rsi_confirm_msg}
{part_str}
━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M:%S')} | GVN Master Algo
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
    
    def alert_wind(self, symbol, wind_dir, call_pct, put_pct, support, resistance, battle_status, ce_vol, pe_vol, pcr, smart_money, trend_type, is_expiry=False, direction_details=None,
                   max_ce_oi_strike=0, max_pe_oi_strike=0, max_ce_oi_val=0, max_pe_oi_val=0,
                   max_ce_oi_pct_strike=0, max_pe_oi_pct_strike=0, max_ce_oi_pct_val=0.0, max_pe_oi_pct_val=0.0,
                   nifty_rsi=50.0, rsi_confirm_msg="", participant_data=None):
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
            direction_details=direction_details,
            max_ce_oi_strike=max_ce_oi_strike,
            max_pe_oi_strike=max_pe_oi_strike,
            max_ce_oi_val=max_ce_oi_val,
            max_pe_oi_val=max_pe_oi_val,
            max_ce_oi_pct_strike=max_ce_oi_pct_strike,
            max_pe_oi_pct_strike=max_pe_oi_pct_strike,
            max_ce_oi_pct_val=max_ce_oi_pct_val,
            max_pe_oi_pct_val=max_pe_oi_pct_val,
            nifty_rsi=nifty_rsi,
            rsi_confirm_msg=rsi_confirm_msg,
            participant_data=participant_data
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

    def send_alert(self, text):
        """Send direct message (compatibility alias for send_direct_message)"""
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
