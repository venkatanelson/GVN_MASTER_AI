
import time
import json
import logging
from datetime import datetime
import nse_option_chain
import gvn_levels_engine
from gvn_telegram_engine import TelegramAlertManager
from gvn_paper_trading_engine import PaperTradingManager
from broker_api import place_order_universal
import shared_data
import gvn_data_bank

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_AI_Delta60")

class GVNAiDelta60Engine:
    """
    GVN Master AI Brain v8.0 - Maximum Safety Edition
    - Integrated Admin Kill Switch
    - Auto Square-off on Kill/OFF status
    - Dynamic Position Sizing (Capital Based)
    - Multi-Stage Exit Strategy
    """
    
    def __init__(self, bot_token=None, chat_id=None):
        self.memory = {
            "active_trades": {},
            "oi_trend": "NEUTRAL"
        }
        self.indices = ["NIFTY", "SENSEX"]
        self.is_running = False
        
        if bot_token and chat_id:
            self.telegram = TelegramAlertManager(bot_token, chat_id)
        else:
            self.telegram = None
            
        self.paper_trading = PaperTradingManager().get_executor()
        self.last_cleanup_date = None
        self.last_snapshot_time = 0
        gvn_data_bank.init_db()

    def run_ai_loop(self):
        self.is_running = True
        logger.info("🛡️ [GVN SAFETY BRAIN v8.0] Kill-Switch & Auto-Square-off Active...")
        
        while self.is_running:
            try:
                # 🛡️ SAFETY CHECK: Is Algo ON or Kill Switch Active?
                if not self._check_safety_status():
                    time.sleep(5)
                    continue

                # 🧹 WEEKLY EXPIRY CLEANUP
                self._handle_weekly_cleanup()

                for index in self.indices:
                    chain = nse_option_chain.fetch_nse_option_chain(index)
                    if not chain or "records" not in chain: continue
                    
                    records = chain["records"]
                    spot = records.get("underlyingValue", shared_data.market_data.get(index, 25000))
                    
                    # 1. Update Market Score
                    self._sync_sentiment(records)
                    
                    # 📊 AI STATUS LOG (Every 30 seconds)
                    if int(time.time()) % 30 < 2:
                        score = shared_data.market_pulse.get("score", 0)
                        logger.info(f"🤖 [AI BRAIN] {index} Spot: {spot} | Market Score: {score} | Trades: {len(self.memory['active_trades'])}")

                    # 2. Monitor & Execute
                    strikes = self._pick_gvn_14_strikes(records, spot, index)
                    
                    # 📸 PERIODIC SNAPSHOT (Every 5 minutes)
                    if time.time() - self.last_snapshot_time > 300:
                        self._save_market_snapshot(index, strikes)
                        self.last_snapshot_time = time.time()

                    for strike in strikes:
                        self._manage_trade_cycle(index, strike)
                
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Safety Loop Error: {e}")
                time.sleep(5)

    def _check_safety_status(self):
        """Checks DB for Kill Switch or OFF status and squares off if needed"""
        # This reads from the shared_data which is updated by app.py
        is_killed = shared_data.market_pulse.get("admin_kill_switch", False)
        is_off = shared_data.market_pulse.get("algo_status", "OFF") == "OFF"
        
        # 🕒 AUTO SQUARE-OFF CUTOFF (3:10 PM IST)
        now = datetime.now()
        time_val = now.hour + (now.minute / 60.0)
        is_time_cutoff = time_val >= 15.166
        
        if is_killed or is_off or is_time_cutoff:
            if self.memory["active_trades"]:
                reason = "Auto Square-off @ 15:10 ⏰" if is_time_cutoff else "EMERGENCY SQUARE-OFF"
                logger.warning(f"🚨 [{reason}] Squaring off all positions immediately!")
                if self.telegram: 
                    self.telegram.send_alert(f"⏰ <b>AUTO SQUARE-OFF CUTOFF (3:10 PM IST) ACTIVATED</b> ⏰\nSquaring off all positions!")
                
                # Close all active trades
                for key in list(self.memory["active_trades"].keys()):
                    trade = self.memory["active_trades"][key]
                    # Simulate or Execute SELL Order for all lots
                    strike_val = key.split('_')[0]
                    opt_type = key.split('_')[1]
                    self._fire_order(strike_val, {"ltp": 0, "strike": strike_val, "type": opt_type}, "SELL", trade["total_lots"], reason)
                    paper_id = trade.get("paper_id")
                    if paper_id:
                        self.paper_trading.execute_paper_sell(paper_id, exit_price=0, exit_reason="AUTO_SQUARE_OFF_310PM")
                
                self.memory["active_trades"] = {}
            return False
        return True

    def _handle_weekly_cleanup(self):
        """Runs cleanup at 6:00 PM (18:00) every Thursday (Expiry Day)"""
        now = datetime.now()
        # Thursday is weekday 3 (Monday is 0)
        if now.weekday() == 3 and now.hour == 18 and now.minute == 0 and self.last_cleanup_date != now.date():
            logger.info("🧹 [GVN WEEKLY CLEANUP] Starting Expiry Day database maintenance...")
            gvn_data_bank.cleanup_old_data(days=7)
            self.last_cleanup_date = now.date()
            if self.telegram:
                self.telegram.send_alert("🧹 <b>GVN WEEKLY CLEANUP</b>\nExpiry Day maintenance complete. Data Bank refreshed for next cycle.")

    def _save_market_snapshot(self, symbol, strikes):
        """Saves current strikes data to the Data Bank"""
        gvn_data_bank.save_option_snapshot(symbol, strikes)
        logger.info(f"📸 [GVN DATA BANK] Saved snapshot for {symbol}")

    def _sync_sentiment(self, records):
        tot_ce = records.get("filtered", {}).get("CE", {}).get("totOI", 1)
        tot_pe = records.get("filtered", {}).get("PE", {}).get("totOI", 1)
        ratio = tot_pe / tot_ce
        shared_data.market_pulse["score"] = int(min(ratio * 50, 100))

    def _pick_gvn_14_strikes(self, records, spot, symbol):
        """
        Dynamically selects exactly 14 strikes per index (7 CE and 7 PE):
        - CE: 4 ITM (delta ~0.60), 3 OTM (delta ~0.46)
        - PE: 4 ITM (delta ~0.60), 3 OTM (delta ~0.46)
        """
        ce_itm_candidates = []
        ce_otm_candidates = []
        pe_itm_candidates = []
        pe_otm_candidates = []
        
        for item in records.get("data", []):
            strike_price = item.get("strikePrice") or item.get("strike")
            if not strike_price:
                continue
                
            for opt_type in ["CE", "PE"]:
                if opt_type in item:
                    opt = item[opt_type]
                    
                    # Extract or compute delta
                    delta = opt.get("delta")
                    if delta is None or delta == 0:
                        try:
                            # Compute using Black-Scholes if missing
                            iv = opt.get("impliedVolatility", 16.5) or 16.5
                            sigma = iv / 100.0
                            today = datetime.now()
                            expiry_weekday = 4 if symbol == "SENSEX" else 3
                            days_to_expiry = max(1, (expiry_weekday - today.weekday()) % 7)
                            T = days_to_expiry / 365.0
                            r = 0.07
                            delta = abs(nse_option_chain.calculate_delta(spot, strike_price, T, r, sigma, opt_type))
                        except Exception:
                            # Proportional fallback estimation
                            if opt_type == "CE":
                                delta = 0.5 - ((strike_price - spot) / spot)
                            else:
                                delta = 0.5 + ((strike_price - spot) / spot)
                            delta = min(0.99, max(0.01, abs(delta)))
                    else:
                        delta = abs(delta)
                    
                    strike_data = {
                        "strike": strike_price,
                        "type": opt_type,
                        "ltp": opt.get("lastPrice", opt.get("lastTradedPrice", 0)),
                        "delta": delta,
                        "oi": opt.get("openInterest", opt.get("oi", 0)),
                        "oi_change": opt.get("changeinOpenInterest", opt.get("oi_change", 0)),
                        "volume": opt.get("totalTradedVolume", opt.get("volume", 0)),
                        "high_915": opt.get("high_915", opt.get("lastPrice", 0) + 15),
                        "low_915": opt.get("low_915", opt.get("lastPrice", 0) - 15),
                        "symbol": opt.get("symbol") or opt.get("tradingSymbol") or f"{symbol}{strike_price}{opt_type}"
                    }
                    
                    if opt_type == "CE":
                        if strike_price <= spot:
                            ce_itm_candidates.append(strike_data)
                        else:
                            ce_otm_candidates.append(strike_data)
                    else: # PE
                        if strike_price >= spot:
                            pe_itm_candidates.append(strike_data)
                        else:
                            pe_otm_candidates.append(strike_data)
                            
        # Select 4 CE ITM closest to delta 0.60
        ce_itm_selected = sorted(ce_itm_candidates, key=lambda x: abs(x["delta"] - 0.60))[:4]
        # Select 3 CE OTM closest to delta 0.46
        ce_otm_selected = sorted(ce_otm_candidates, key=lambda x: abs(x["delta"] - 0.46))[:3]
        
        # Select 4 PE ITM closest to delta 0.60
        pe_itm_selected = sorted(pe_itm_candidates, key=lambda x: abs(x["delta"] - 0.60))[:4]
        # Select 3 PE OTM closest to delta 0.46
        pe_otm_selected = sorted(pe_otm_candidates, key=lambda x: abs(x["delta"] - 0.46))[:3]
        
        selected = ce_itm_selected + ce_otm_selected + pe_itm_selected + pe_otm_selected
        return selected

    def _manage_trade_cycle(self, symbol, strike):
        # 🎯 GVN SCANNER: Only execute trades if this symbol is the active dashboard selection
        active_index = getattr(shared_data, 'active_dashboard_symbol', 'NIFTY').upper()
        if symbol.upper() != active_index:
            return

        session_params = nse_option_chain.get_session_parameters()

        key = f"{strike['strike']}_{strike['type']}"
        ltp = strike["ltp"]
        # ⚡ REAL-TIME WEBSOCKET LTP OVERRIDE (Sub-second execution)
        search_key = f"{int(strike['strike'])} {strike['type']}"
        real_ltp = shared_data.market_data.get(search_key, 0)
        if real_ltp > 0:
            ltp = real_ltp
            
        # 🔒 GVN SAFE LEVELS CALCULATION: Double check with real recorded 9:15 candles to avoid missing data
        high_915 = strike.get("high_915", 0)
        low_915 = strike.get("low_915", 0)
        try:
            real_ohlc = nse_option_chain.get_real_option_915_ohlc(symbol, strike["strike"], strike["type"])
            if real_ohlc:
                high_915, low_915 = real_ohlc
        except Exception as ohlc_err:
            pass
            
        levels = gvn_levels_engine.calculate_gvn_levels(high_915, low_915)
        if not levels: return
        
        # 📊 GVN RSI 15 Trend Calculation
        idx_rsi = 50.0
        opt_rsi = 50.0
        try:
            # Initialize caches
            if "rsi_last_fetch" not in self.memory: self.memory["rsi_last_fetch"] = {}
            if "rsi_closes" not in self.memory: self.memory["rsi_closes"] = {}
            
            now = time.time()
            idx_cache_key = f"{symbol}_index_closes"
            idx_last_fetch = self.memory["rsi_last_fetch"].get(idx_cache_key, 0)
            idx_closes = self.memory["rsi_closes"].get(idx_cache_key, [])
            
            if now - idx_last_fetch > 30 or not idx_closes:
                fetched_closes = self._fetch_closes_from_api(symbol)
                if fetched_closes:
                    self.memory["rsi_closes"][idx_cache_key] = fetched_closes
                    idx_closes = fetched_closes
                    self.memory["rsi_last_fetch"][idx_cache_key] = now
                    
            opt_cache_key = f"{key}_option_closes"
            opt_last_fetch = self.memory["rsi_last_fetch"].get(opt_cache_key, 0)
            opt_closes = self.memory["rsi_closes"].get(opt_cache_key, [])
            
            if now - opt_last_fetch > 30 or not opt_closes:
                fetched_closes = self._fetch_closes_from_api(symbol, strike['strike'], strike['type'])
                if fetched_closes:
                    self.memory["rsi_closes"][opt_cache_key] = fetched_closes
                    opt_closes = fetched_closes
                    self.memory["rsi_last_fetch"][opt_cache_key] = now
                    
            # Compute live values
            idx_closes_live = list(idx_closes)
            idx_spot = shared_data.market_data.get(symbol, 0)
            if idx_spot <= 0 and symbol == "NIFTY":
                idx_spot = shared_data.market_data.get("NIFTY 50", 0)
            if idx_spot > 0 and idx_closes_live:
                idx_closes_live.append(float(idx_spot))
                
            opt_closes_live = list(opt_closes)
            if ltp > 0 and opt_closes_live:
                opt_closes_live.append(float(ltp))
                
            if len(idx_closes_live) >= 16:
                idx_rsi = self._compute_rsi(idx_closes_live, period=15)
            if len(opt_closes_live) >= 16:
                opt_rsi = self._compute_rsi(opt_closes_live, period=15)
                
            # Cache values in shared_data
            shared_data.market_pulse[f"{symbol}_rsi_15"] = idx_rsi
            shared_data.market_pulse[f"{key}_rsi_15"] = opt_rsi
        except Exception as rsi_calc_err:
            logger.error(f"❌ GVN RSI Calculation Error: {rsi_calc_err}")

        # 🚨 GVN DUAL-SYNC LIVE ALERT CROSSOVER CHECK
        try:
            self._check_gvn_sync_alerts(symbol, strike, ltp, levels, idx_rsi=idx_rsi, opt_rsi=opt_rsi)
        except Exception as alert_err:
            logger.error(f"❌ Error in GVN Sync Alert Check: {alert_err}")


        
        # 🔒 PERSISTENT MORNING LOCK: Only allow trades on the morning locked strike
        locked_strike = 0
        try:
            import os
            import json
            if os.path.exists("morning_locked_strikes.json"):
                with open("morning_locked_strikes.json", "r") as f:
                    lock_data = json.load(f)
                if lock_data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                    locked_strike = lock_data.get(symbol, {}).get(strike["type"], 0)
        except: pass

        if locked_strike > 0 and int(strike["strike"]) != locked_strike:
            # Skip new entries for non-locked strikes, but manage active trades if they exist
            if key not in self.memory["active_trades"]:
                return
        
        if "alerted_levels" not in self.memory:
            self.memory["alerted_levels"] = {}

        if key not in self.memory["active_trades"]:
            # CE Entry: Bullish Sentiment (Score >= 65) or UP WIND
            # PE Entry: Bearish Sentiment (Score <= 35) or DOWN WIND
            
            # Fetch latest wind direction from the Database (Engine 1)
            latest_wind = gvn_data_bank.get_latest_wind_status(symbol)
            if latest_wind:
                wind_dir = latest_wind["wind_direction"]
                wind_power = latest_wind["wind_power"]
                # Keep shared_data.market_pulse in sync
                shared_data.market_pulse["wind_direction"] = wind_dir
                shared_data.market_pulse["wind_power"] = wind_power
                shared_data.market_pulse["trend_type"] = latest_wind["trend_type"]
                shared_data.market_pulse["smart_money"] = latest_wind["smart_money"]
            else:
                wind_dir = shared_data.market_pulse.get("wind_direction", "NEUTRAL")
                wind_power = shared_data.market_pulse.get("wind_power", 1.0)
            
            is_bullish = strike['type'] == 'CE' and (shared_data.market_pulse.get("score", 50) >= 65 or any(w in wind_dir for w in ["UP WIND", "SHORT COVERING"]))
            is_bearish = strike['type'] == 'PE' and (shared_data.market_pulse.get("score", 50) <= 35 or any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING"]))
            
            # 🛡️ THE GVN WIND FILTER (AVOIDING 12-PT SL HITS)
            # 1. Reject CE entries if the wind is blowing DOWN
            if strike['type'] == 'CE' and any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING"]):
                is_bullish = False
            # 2. Reject PE entries if the wind is blowing UP
            if strike['type'] == 'PE' and any(w in wind_dir for w in ["UP WIND", "SHORT COVERING"]):
                is_bearish = False
            # 3. Reject ALL entries if it's a Trap / Premium Eating zone
            if "PREMIUM EATING" in wind_dir or wind_power < 0.8:
                is_bullish = False
                is_bearish = False

            # 4. 🛡️ F&O NIFTY 50 UNDERLYING STOCKS ALIGNMENT FILTER (Second Additional Confirmation)
            nifty50_trend = shared_data.market_pulse.get("nifty50_trend_signal", "NEUTRAL")
            if nifty50_trend in ["STRONG BEARISH", "MODERATE BEARISH"] and strike['type'] == 'CE':
                logger.info(f"🚫 [NIFTY 50 STOCK FILTER] CE entry blocked. Nifty 50 trend is {nifty50_trend}.")
                is_bullish = False
            if nifty50_trend in ["STRONG BULLISH", "MODERATE BULLISH"] and strike['type'] == 'PE':
                logger.info(f"🚫 [NIFTY 50 STOCK FILTER] PE entry blocked. Nifty 50 trend is {nifty50_trend}.")
                is_bearish = False

            is_fake_crossover = False
            # 5. GVN Dual-Sync Crossover Verification Filter (True vs Fake Breakouts)
            try:
                idx_high, idx_low = 0, 0
                if symbol == "NIFTY":
                    idx_high = 24110.75
                    idx_low = 24032.35
                else:
                    bench = shared_data.gvn_915_benchmark.get(symbol, {})
                    if bench.get("high", 0) > 0:
                        idx_high = bench["high"]
                        idx_low = bench["low"]
                
                if idx_high > 0 and idx_low > 0:
                    idx_levels = gvn_levels_engine.calculate_gvn_levels(idx_high, idx_low, is_index=True)
                    if idx_levels:
                        spot_price = shared_data.market_data.get(symbol, 0)
                        if spot_price <= 0 and symbol == "NIFTY":
                            spot_price = shared_data.market_data.get("NIFTY 50", 0)
                        
                        opt_i5 = levels.get("i5", 0) # Option 0.5 level
                        
                        if strike['type'] == 'CE' and ltp >= opt_i5:
                            idx_i3 = idx_levels.get("i3", 0) # Index 0.618 level
                            if spot_price < idx_i3:
                                logger.info(f"🚫 [GVN SYNC FILTER] FAKE CE BREAKOUT: Option CE LTP {ltp} >= {opt_i5} (0.5 level) but Spot {spot_price} is below Index 0.618 Level {idx_i3}.")
                                is_fake_crossover = True
                                is_bullish = False
                                
                        elif strike['type'] == 'PE' and ltp >= opt_i5:
                            idx_i5 = idx_levels.get("i5", 0) # Index 0.5 level
                            if spot_price > idx_i5:
                                logger.info(f"🚫 [GVN SYNC FILTER] FAKE PE BREAKOUT: Option PE LTP {ltp} >= {opt_i5} (0.5 level) but Spot {spot_price} is above Index 0.5 Level {idx_i5}.")
                                is_fake_crossover = True
                                is_bearish = False
            except Exception as sync_filt_err:
                logger.error(f"❌ GVN Sync Filter Error: {sync_filt_err}")

            is_rsi_unconfirmed = False
            # 6. GVN RSI 15 Trend & 50-Crossover Validation Filter
            try:
                # Apply RSI 50 Validation Filter to block non-confirming trades
                if strike['type'] == 'CE':
                    # CE buy requires CE Option RSI > 50 and Nifty Index RSI > 50
                    if opt_rsi < 50.0 or idx_rsi < 50.0:
                        logger.info(f"🚫 [GVN RSI FILTER] CE entry blocked. Option CE RSI: {opt_rsi:.2f}, Nifty Spot RSI: {idx_rsi:.2f} (Both must be > 50).")
                        is_rsi_unconfirmed = True
                        is_bullish = False
                elif strike['type'] == 'PE':
                    # PE buy requires PE Option RSI > 50 and Nifty Index RSI < 50 (bearish index trend)
                    if opt_rsi < 50.0 or idx_rsi > 50.0:
                        logger.info(f"🚫 [GVN RSI FILTER] PE entry blocked. Option PE RSI: {opt_rsi:.2f}, Nifty Spot RSI: {idx_rsi:.2f} (Option must be > 50, Index must be < 50).")
                        is_rsi_unconfirmed = True
                        is_bearish = False
            except Exception as rsi_filt_err:
                logger.error(f"❌ GVN RSI Filter Error: {rsi_filt_err}")




            if "last_ltps" not in self.memory:
                self.memory["last_ltps"] = {}
            previous_ltp = self.memory["last_ltps"].get(key, ltp)
            self.memory["last_ltps"][key] = ltp
            
            # GVN Pro Alerts - Check proximity (1% or 1 point buffer) to i5, i6, i7 (DISABLED AS PER USER REQUEST TO PREVENT ALERT SPAM)
            # if "pro_alerts_sent" not in self.memory:
            #     self.memory["pro_alerts_sent"] = {}
            #     
            # for lvl_name in ["i5", "i6", "i7"]:
            #     lvl_val = levels.get(lvl_name, 0)
            #     if lvl_val > 0:
            #         dist = abs(ltp - lvl_val)
            #         # Check if within 1 point or 1% buffer
            #         if dist <= 1.0 or dist <= (lvl_val * 0.01):
            #             alert_time_key = f"{key}_{lvl_name}_pro_alert"
            #             last_alert_time = self.memory["pro_alerts_sent"].get(alert_time_key, 0)
            #             # Alert at most once every 5 minutes per level per strike
            #             if time.time() - last_alert_time > 300:
            #                 alert_msg = (
            #                     f"⚠️ <b>GVN PRO ALERT: APPROACHING {lvl_name.upper()}</b> ⚠️\n"
            #                     f"🎯 Symbol: {symbol} {strike['strike']} {strike['type']}\n"
            #                     f"⚡ Level: <b>{lvl_name.upper()} ({lvl_val})</b>\n"
            #                     f"💸 Current Price: <b>₹{ltp}</b>\n"
            #                     f"📏 Distance: {round(dist, 2)} pts away"
            #                 )
            #                 logger.info(f"[PRO ALERT] {symbol} {strike['strike']} {strike['type']} is approaching {lvl_name.upper()} ({lvl_val}) @ {ltp}")
            #                 if self.telegram:
            #                     self.telegram.send_alert(alert_msg)
            #                 self.memory["pro_alerts_sent"][alert_time_key] = time.time()

            # GVN Levels sorted in ascending order: [i1, i7, i6, i5, i3, i2, i0]
            sorted_lvls = sorted([levels['i1'], levels['i7'], levels['i6'], levels['i5'], levels['i3'], levels['i2'], levels['i0']])
            
            # 🔄 GVN LADDER RE-ENTRY ENGINE (Dot-to-Dot Pullback Re-entry)
            if "last_completed_targets" not in self.memory:
                self.memory["last_completed_targets"] = {}
            if "target_pullback_flags" not in self.memory:
                self.memory["target_pullback_flags"] = {}
                
            last_tgt = self.memory["last_completed_targets"].get(key, 0)
            if last_tgt > 0:
                # 1. Track Pullback (Price must dip below target level to qualify for re-entry)
                if ltp < last_tgt - 0.50:
                    self.memory["target_pullback_flags"][key] = True
                
                # 2. Trigger Re-entry (When price touches/crosses the target level again)
                if self.memory["target_pullback_flags"].get(key, False):
                    is_retrigger = False
                    if previous_ltp < last_tgt <= ltp:
                        is_retrigger = True
                    elif abs(ltp - last_tgt) <= 0.20:
                        is_retrigger = True
                        
                    if is_retrigger and session_params.get("enable_new_trades", True):
                        # Find the next higher GVN level as the new target
                        new_tgt = last_tgt + 30.0
                        for idx, lvl in enumerate(sorted_lvls):
                            if abs(lvl - last_tgt) < 0.50:
                                if idx + 1 < len(sorted_lvls):
                                    new_tgt = sorted_lvls[idx + 1]
                                break
                                
                        new_sl = last_tgt - 12.0 # Strict 12-point Stop Loss
                        
                        # Reset pullback flag for this strike
                        self.memory["target_pullback_flags"][key] = False
                        
                        # Execute
                        self._execute_gvn_level_trade(symbol, strike, ltp, new_tgt, new_sl, f"GVN Level Re-entry (near {last_tgt:.2f})")
                        return

            # GVN Pro Level Touch/Crossover checks: strictly 1st Entry (i5), intermediate Entry (i6), and 2nd Entry (i7)
            i5_val = levels.get("i5", 0)
            i6_val = levels.get("i6", 0)
            i7_val = levels.get("i7", 0)
            
            triggered_level_name = None
            entry_level_val = None
            target_val = None
            sl_val = None
            
            is_exp = (datetime.now().weekday() == 3)
            
            # Enforce Index Level Touch Check to avoid fake entries (Bypassed as per user request to trigger trades directly on option levels)
            is_idx_i5_touched = True
            is_idx_i6_touched = True
            is_idx_i7_touched = True
            
            # 🌪️ GVN LEVEL ACCELERATION / INDEX-OPTION LEVEL DIVERGENCE ENTRY
            is_level_accel_setup = False
            index_benchmark = shared_data.gvn_915_benchmark.get(symbol)
            if index_benchmark and index_benchmark.get("captured"):
                idx_levels = gvn_levels_engine.calculate_gvn_levels(
                    index_benchmark["high"], 
                    index_benchmark["low"], 
                    index_benchmark.get("close"),
                    is_index=True
                )
                if idx_levels:
                    idx_i3 = idx_levels.get("i3", 0)  # 0.618 level
                    idx_i5 = idx_levels.get("i5", 0)  # 0.50 level
                    idx_spot = shared_data.market_data.get(symbol, 0)
                    
                    if idx_i3 > 0 and idx_i5 > 0 and idx_spot > 0:
                        min_idx = min(idx_i3, idx_i5)
                        max_idx = max(idx_i3, idx_i5)
                        
                        # Check if Index Spot is between Level 6 (i3) and Level 5 (i5)
                        if min_idx <= idx_spot <= max_idx:
                            # 1. Bearish Put Acceleration (Put option premium explodes as spot falls)
                            if strike['type'] == 'PE' and (any(w in wind_dir for w in ["DOWN WIND", "LONG UNWINDING", "PE Acceleration"]) or shared_data.market_pulse.get("score", 50) <= 45):
                                if i7_val > 0 and (previous_ltp < i7_val <= ltp or abs(ltp - i7_val) <= 0.30):
                                    is_level_accel_setup = True
                                    triggered_level_name = "I7_ACCEL_PE"
                                    entry_level_val = ltp
                                    target_lvl_name = "i6"
                                    target_val = levels.get("i6", ltp + 25.0)
                                    sl_val = round(ltp - 12.0, 2)
                                    logger.info(f"🌪️ [LEVEL ACCELERATION] PE Acceleration entry triggered on {symbol} PE {strike['strike']} @ {ltp}")
                                    
                            # 2. Bullish Call Acceleration (Call option premium explodes as spot rises)
                            elif strike['type'] == 'CE' and (any(w in wind_dir for w in ["UP WIND", "SHORT COVERING", "CE Acceleration"]) or shared_data.market_pulse.get("score", 50) >= 55):
                                if i7_val > 0 and (previous_ltp < i7_val <= ltp or abs(ltp - i7_val) <= 0.30):
                                    is_level_accel_setup = True
                                    triggered_level_name = "I7_ACCEL_CE"
                                    entry_level_val = ltp
                                    target_lvl_name = "i6"
                                    target_val = levels.get("i6", ltp + 25.0)
                                    sl_val = round(ltp - 12.0, 2)
                                    logger.info(f"🌪️ [LEVEL ACCELERATION] CE Acceleration entry triggered on {symbol} CE {strike['strike']} @ {ltp}")

            if is_fake_crossover or is_rsi_unconfirmed:
                is_level_accel_setup = False


            # Check i5 (1st Entry)
            if not triggered_level_name and i5_val > 0:
                is_i5_triggered = False
                if previous_ltp < i5_val <= ltp:
                    is_i5_triggered = True
                elif abs(ltp - i5_val) <= 0.20:
                    is_i5_triggered = True
                    
                if is_i5_triggered and is_idx_i5_touched:
                    triggered_level_name = "I5"
                    entry_level_val = i5_val
                    # Target is i3 (same as normal days)
                    target_lvl_name = "i3"
                    target_val = levels.get(target_lvl_name, ltp + 12.0)
                    sl_val = round(i5_val - 12.0, 2)
                    
            # Check i6 (Intermediate Entry) - only if i5 not triggered
            if not triggered_level_name and i6_val > 0:
                is_i6_triggered = False
                if previous_ltp < i6_val <= ltp:
                    is_i6_triggered = True
                elif abs(ltp - i6_val) <= 0.20:
                    is_i6_triggered = True
                    
                if is_i6_triggered and is_idx_i6_touched:
                    triggered_level_name = "I6"
                    entry_level_val = i6_val
                    # Target is i5 (same as normal days)
                    target_lvl_name = "i5"
                    target_val = levels.get(target_lvl_name, ltp + 12.0)
                    sl_val = round(i6_val - 12.0, 2)
                    
            # Check i7 (2nd Entry) - only if i5/i6 not triggered
            if not triggered_level_name and i7_val > 0:
                is_i7_triggered = False
                if previous_ltp < i7_val <= ltp:
                    is_i7_triggered = True
                elif abs(ltp - i7_val) <= 0.20:
                    is_i7_triggered = True
                    
                if is_i7_triggered and is_idx_i7_touched:
                    triggered_level_name = "I7"
                    entry_level_val = i7_val
                    # Target is i6 (same as normal days)
                    target_lvl_name = "i6"
                    target_val = levels.get(target_lvl_name, ltp + 12.0)
                    sl_val = round(i7_val - 12.0, 2)
                    
            if triggered_level_name:
                is_allowed = True
                if "ACCEL" not in triggered_level_name:
                    pref_level_val = levels["i5"] # Always i5 preference (same as normal days)
                    pref_key = f"{key}_pref_traded"
                    
                    # Force first morning entry to be near preference level
                    if not self.memory.get(pref_key, False):
                        if abs(entry_level_val - pref_level_val) > 1.5:
                            is_allowed = False
                        
                if is_allowed and session_params.get("enable_new_trades", True) and (is_level_accel_setup or (strike['type'] == 'CE' and is_bullish) or (strike['type'] == 'PE' and is_bearish)):
                    if "ACCEL" not in triggered_level_name:
                        self.memory[pref_key] = True
                    # Execute
                    self._execute_gvn_level_trade(symbol, strike, entry_level_val, target_val, sl_val, f"GVN Level Entry ({triggered_level_name} @ {entry_level_val:.2f})")
        else:
            trade = self.memory["active_trades"][key]
            
            # Exit check: Target Hit
            if ltp >= trade["target"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"], f"Full Exit (Target Hit @ {trade['target']})")
                paper_id = trade.get("paper_id")
                if paper_id:
                    self.paper_trading.execute_paper_sell(paper_id, exit_price=ltp, exit_reason="TARGET_HIT")
                
                # 🔄 Save last hit target for GVN Re-entry tracking
                if "last_completed_targets" not in self.memory:
                    self.memory["last_completed_targets"] = {}
                self.memory["last_completed_targets"][key] = trade["target"]
                
                if "target_pullback_flags" not in self.memory:
                    self.memory["target_pullback_flags"] = {}
                self.memory["target_pullback_flags"][key] = False
                
                del self.memory["active_trades"][key]
                
            # Exit check: Stop Loss Hit
            elif ltp <= trade["sl"]:
                self._fire_order(symbol, strike, "SELL", trade["total_lots"], f"Full Exit (SL Hit @ {trade['sl']})")
                paper_id = trade.get("paper_id")
                if paper_id:
                    self.paper_trading.execute_paper_sell(paper_id, exit_price=ltp, exit_reason="SL_HIT")
                del self.memory["active_trades"][key]

    def _execute_gvn_level_trade(self, symbol, strike, entry_price, target, sl, reason):
        balance = shared_data.market_data.get("available_cash", 20000)
        target_lots = max(1, min(5, int(balance / 10000)))
        key = f"{strike['strike']}_{strike['type']}"
        
        # Execute paper trade and store the ID
        paper_trade = self.paper_trading.execute_paper_buy(symbol, strike["strike"], strike["type"], entry_price, target, sl, target_lots * 50)
        paper_id = paper_trade["id"] if paper_trade else None
        
        self.memory["active_trades"][key] = {
            "entry": entry_price, 
            "target": target, 
            "sl": sl, 
            "total_lots": target_lots,
            "paper_id": paper_id
        }
        self._fire_order(symbol, strike, "BUY", target_lots, reason, target_price=target, sl_price=sl)

    def _fire_order(self, symbol, strike, side, qty, reason, target_price=None, sl_price=None):
        full_symbol = strike.get("symbol", f"{symbol}{strike['strike']}{strike['type']}")
        tsym = f"{symbol}_{int(strike['strike'])}_{strike['type']}"
        
        if side == "SELL":
            alert = (
                f"🛑 <b>GVN MASTER ALGO - POSITION CLOSED</b> 🛑\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Symbol: <b>{tsym}</b>\n"
                f"⚡ Reason: <b>{reason}</b>\n"
                f"💸 Exit Price: <b>₹{strike.get('ltp', 0.0)}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Position closed successfully"
            )
            if self.telegram: self.telegram.send_alert(alert)
        else:
            # Calculate levels to display in the alert
            levels = gvn_levels_engine.calculate_gvn_levels(strike["high_915"], strike["low_915"])
            if target_price is None:
                target_price = strike.get("ltp", 0.0) + 12.0
            if sl_price is None:
                sl_price = strike.get("ltp", 0.0) - 12.0
            
            level_name = "I3"
            if "accel" in reason.lower(): level_name = "I7 (Level Acceleration 🌪️)"
            elif "i5" in reason.lower(): level_name = "I5"
            elif "i7" in reason.lower(): level_name = "I7"
            elif "i1" in reason.lower() or "i0" in reason.lower(): level_name = "I1/I0"
            elif "i6" in reason.lower(): level_name = "I6"
            elif "i2" in reason.lower(): level_name = "I2"
            elif "i3" in reason.lower(): level_name = "I3"
            
            if levels and target_price is None:
                is_exp = (datetime.now().weekday() == 3)
                if level_name == "I5":
                    target_price = levels["i2"] if is_exp else levels["i3"]
                    sl_price = round(levels["i5"] - 12.0, 2)
                elif level_name == "I6":
                    target_price = levels["i3"] if is_exp else levels["i5"]
                    sl_price = round(levels["i6"] - 12.0, 2)
                elif level_name == "I7":
                    target_price = levels["i5"] if is_exp else levels["i6"]
                    sl_price = round(levels["i7"] - 12.0, 2)
                elif level_name == "I1/I0":
                    target_price, sl_price = levels["i5"], round(levels["i1"] - 12.0, 2)
                elif level_name == "I3":
                    target_price, sl_price = levels["i2"], round(levels["i3"] - 12.0, 2)

            alert = (
                f"🚀 <b>GVN MASTER ALGO - NEW ENTRY</b> 🚀\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Symbol: <b>{tsym}</b>\n"
                f"⚡ Level Triggered: <b>{level_name}</b>\n"
                f"💸 Entry Price: <b>₹{strike.get('ltp', 0.0)}</b>\n"
                f"✅ Target: <b>₹{target_price:.2f}</b>\n"
                f"⛔ Stop Loss: <b>₹{sl_price:.2f}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Processed exactly as per GVN Settings"
            )
            if self.telegram: self.telegram.send_alert(alert)

        # 🚀 GVN MULTI-USER DYNAMIC ROUTING ENGINE
        try:
            from app import app, db, User, UserBrokerConfig, AlgoTrade
            
            with app.app_context():
                # Query all active users whose Algo is turned ON and are not blocked
                active_users = User.query.filter_by(algo_status='ON', is_blocked=False).all()
                logger.info(f"🛰️ [GVN MULTI-USER ENGINE] Found {len(active_users)} active users with Algo ON.")
                
                for u in active_users:
                    try:
                        user_lots = u.trade_lots or 1
                        
                        # 1. Check if user has active and approved live subscription
                        is_live_allowed = False
                        if u.user_type == 'LIVE' and u.is_approved:
                            if u.expiry_date and u.expiry_date > datetime.utcnow():
                                is_live_allowed = True
                        
                        # 2. Add trade to their database dashboard
                        new_trade = AlgoTrade(
                            user_id=u.id,
                            symbol=full_symbol,
                            entry_price=float(strike['ltp']) if side == 'BUY' else 0.0,
                            exit_price=float(strike['ltp']) if side == 'SELL' else 0.0,
                            quantity=user_lots * 50, # 1 lot = 50 qty
                            trade_type=side,
                            status='Open' if side == 'BUY' else 'Closed',
                            delta=float(strike.get('delta', 0.60)),
                            sentiment=reason
                        )
                        db.session.add(new_trade)
                        db.session.commit()
                        
                        # 3. If LIVE subscription and API is configured, place REAL trade
                        config = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                        if is_live_allowed and config and config.client_id:
                            creds = config.get_credentials()
                            cfg = {
                                "broker_name": config.broker_name or "Shoonya",
                                "client_id": config.client_id,
                                "password": creds.get('password'),
                                "api_key": creds.get('api_key'),
                                "api_secret": creds.get('api_secret'),
                                "totp_key": creds.get('totp_key'),
                                "webhook_url": config.webhook_url,
                                "tv_secret": config.tv_secret
                            }
                            
                            from broker_api import execute_broker_order_async
                            execute_broker_order_async(cfg, full_symbol, side, user_lots * 50, u.username)
                            logger.info(f"💼 [LIVE ROUTED] real broker order submitted for user {u.username} via {config.broker_name}")
                        else:
                            # Otherwise, run as PAPER / DEMO trade
                            logger.info(f"📊 [PAPER RECORDED] Demo trade saved to dashboard for user {u.username}")
                            
                    except Exception as ex:
                        logger.error(f"❌ Failed executing trade block for user {u.username}: {ex}")
                        
        except Exception as e:
            logger.error(f"❌ Multi-user routing critical failure: {e}")

    def _check_gvn_sync_alerts(self, symbol, strike, ltp, levels, idx_rsi=50.0, opt_rsi=50.0):
        if not self.telegram:
            return
            
        import os
        spot_price = shared_data.market_data.get(symbol, 0)
        if spot_price <= 0:
            spot_price = shared_data.market_data.get("NIFTY 50", 0) if symbol == "NIFTY" else 0
        if spot_price <= 0:
            return
            
        key = f"{strike['strike']}_{strike['type']}"
        
        # Get index GVN levels
        idx_levels = None
        high = 0
        low = 0
        if symbol == "NIFTY":
            high = 24110.75
            low = 24032.35
        else:
            try:
                if os.path.exists("gvn_recorded_915_ohlc.json"):
                    with open("gvn_recorded_915_ohlc.json", "r") as f:
                        rec_data = json.load(f)
                    spot_key = f"{symbol}_SPOT"
                    if spot_key in rec_data.get(symbol, {}):
                        high = rec_data[symbol][spot_key].get("high", 0)
                        low = rec_data[symbol][spot_key].get("low", 0)
            except: pass
            
            if high == 0 or low == 0:
                bench = shared_data.gvn_915_benchmark.get(symbol, {})
                if bench.get("high", 0) > 0:
                    high = bench["high"]
                    low = bench["low"]
                    
        if high > 0 and low > 0:
            idx_levels = gvn_levels_engine.calculate_gvn_levels(high, low, is_index=True)
            
        if not idx_levels:
            return
            
        # Index key levels
        idx_i3 = idx_levels.get("i3", 0) # 0.618
        idx_i5 = idx_levels.get("i5", 0) # 0.500
        idx_i6 = idx_levels.get("i6", 0) # 0.382
        idx_i7 = idx_levels.get("i7", 0) # 0.236
        
        # Calculate Index midpoints
        idx_mid_3_5 = (idx_i3 + idx_i5) / 2
        idx_mid_5_6 = (idx_i5 + idx_i6) / 2
        idx_mid_6_7 = (idx_i6 + idx_i7) / 2
        
        # Option key levels
        opt_i3 = levels.get("i3", 0) # 0.3
        opt_i5 = levels.get("i5", 0) # 0.5
        opt_i6 = levels.get("i6", 0) # 0.6
        opt_i7 = levels.get("i7", 0) # Level 7 (0.236 equivalent)
        
        # Calculate Option midpoints
        opt_mid_3_5 = (opt_i3 + opt_i5) / 2
        opt_mid_5_6 = (opt_i5 + opt_i6) / 2
        opt_mid_6_7 = (opt_i6 + opt_i7) / 2
        
        # Initialize memory tracking
        if "sync_alert_state" not in self.memory:
            self.memory["sync_alert_state"] = {}
            
        state_key = f"{symbol}_{key}"
        prev_state = self.memory["sync_alert_state"].get(state_key)
        
        # Compute current state
        curr_idx_i3_rel = "ABOVE" if spot_price >= idx_i3 else "BELOW"
        curr_idx_mid_3_5_rel = "ABOVE" if spot_price >= idx_mid_3_5 else "BELOW"
        curr_idx_i5_rel = "ABOVE" if spot_price >= idx_i5 else "BELOW"
        curr_idx_mid_5_6_rel = "ABOVE" if spot_price >= idx_mid_5_6 else "BELOW"
        curr_idx_i6_rel = "ABOVE" if spot_price >= idx_i6 else "BELOW"
        curr_idx_mid_6_7_rel = "ABOVE" if spot_price >= idx_mid_6_7 else "BELOW"
        curr_idx_i7_rel = "ABOVE" if spot_price >= idx_i7 else "BELOW"
        
        curr_opt_i3_rel = "ABOVE" if ltp >= opt_i3 else "BELOW"
        curr_opt_mid_3_5_rel = "ABOVE" if ltp >= opt_mid_3_5 else "BELOW"
        curr_opt_i5_rel = "ABOVE" if ltp >= opt_i5 else "BELOW"
        curr_opt_mid_5_6_rel = "ABOVE" if ltp >= opt_mid_5_6 else "BELOW"
        curr_opt_i6_rel = "ABOVE" if ltp >= opt_i6 else "BELOW"
        curr_opt_mid_6_7_rel = "ABOVE" if ltp >= opt_mid_6_7 else "BELOW"
        curr_opt_i7_rel = "ABOVE" if ltp >= opt_i7 else "BELOW"
        
        curr_state = {
            "idx_i3": curr_idx_i3_rel,
            "idx_mid_3_5": curr_idx_mid_3_5_rel,
            "idx_i5": curr_idx_i5_rel,
            "idx_mid_5_6": curr_idx_mid_5_6_rel,
            "idx_i6": curr_idx_i6_rel,
            "idx_mid_6_7": curr_idx_mid_6_7_rel,
            "idx_i7": curr_idx_i7_rel,
            "opt_i3": curr_opt_i3_rel,
            "opt_mid_3_5": curr_opt_mid_3_5_rel,
            "opt_i5": curr_opt_i5_rel,
            "opt_mid_5_6": curr_opt_mid_5_6_rel,
            "opt_i6": curr_opt_i6_rel,
            "opt_mid_6_7": curr_opt_mid_6_7_rel,
            "opt_i7": curr_opt_i7_rel
        }
        
        # Compare states to detect crossover
        is_crossover = False
        change_desc = []
        
        if prev_state:
            # Check Index levels crossover
            if prev_state["idx_i3"] != curr_state["idx_i3"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_i3_rel == 'ABOVE' else 'BELOW'} 0.618 ({idx_i3:.2f})")
            if prev_state.get("idx_mid_3_5") != curr_state["idx_mid_3_5"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_mid_3_5_rel == 'ABOVE' else 'BELOW'} Mid 0.618-0.5 ({idx_mid_3_5:.2f})")
            if prev_state["idx_i5"] != curr_state["idx_i5"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_i5_rel == 'ABOVE' else 'BELOW'} 0.5 ({idx_i5:.2f})")
            if prev_state.get("idx_mid_5_6") != curr_state["idx_mid_5_6"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_mid_5_6_rel == 'ABOVE' else 'BELOW'} Mid 0.5-0.382 ({idx_mid_5_6:.2f})")
            if prev_state["idx_i6"] != curr_state["idx_i6"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_i6_rel == 'ABOVE' else 'BELOW'} 0.382 ({idx_i6:.2f})")
            if prev_state.get("idx_mid_6_7") != curr_state["idx_mid_6_7"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_mid_6_7_rel == 'ABOVE' else 'BELOW'} Mid 0.382-0.236 ({idx_mid_6_7:.2f})")
            if prev_state.get("idx_i7") != curr_state["idx_i7"]:
                is_crossover = True
                change_desc.append(f"Index crossed {'ABOVE' if curr_idx_i7_rel == 'ABOVE' else 'BELOW'} 0.236 ({idx_i7:.2f})")
                
            # Check Option levels crossover
            if prev_state["opt_i3"] != curr_state["opt_i3"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_i3_rel == 'ABOVE' else 'BELOW'} 0.3 Target ({opt_i3:.2f})")
            if prev_state.get("opt_mid_3_5") != curr_state["opt_mid_3_5"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_mid_3_5_rel == 'ABOVE' else 'BELOW'} Mid 0.3-0.5 ({opt_mid_3_5:.2f})")
            if prev_state["opt_i5"] != curr_state["opt_i5"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_i5_rel == 'ABOVE' else 'BELOW'} 0.5 level ({opt_i5:.2f})")
            if prev_state.get("opt_mid_5_6") != curr_state["opt_mid_5_6"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_mid_5_6_rel == 'ABOVE' else 'BELOW'} Mid 0.5-0.6 ({opt_mid_5_6:.2f})")
            if prev_state["opt_i6"] != curr_state["opt_i6"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_i6_rel == 'ABOVE' else 'BELOW'} 0.6 level ({opt_i6:.2f})")
            if prev_state.get("opt_mid_6_7") != curr_state["opt_mid_6_7"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_mid_6_7_rel == 'ABOVE' else 'BELOW'} Mid 0.6-0.7 ({opt_mid_6_7:.2f})")
            if prev_state.get("opt_i7") != curr_state["opt_i7"]:
                is_crossover = True
                change_desc.append(f"Option crossed {'ABOVE' if curr_opt_i7_rel == 'ABOVE' else 'BELOW'} Level 7 ({opt_i7:.2f})")
        else:
            is_crossover = False
            
        self.memory["sync_alert_state"][state_key] = curr_state
        
        if is_crossover:
            # Build beautiful message
            timing = datetime.now().strftime("%I:%M:%S %p")
            
            # Index status string
            idx_trend_icon = "🟢" if spot_price >= idx_i5 else "🔴"
            idx_i5_status = "ABOVE 🟢" if spot_price >= idx_i5 else "BELOW 🔴"
            
            # Find next target and active channel for index
            active_channel = "Neutral Zone"
            if spot_price >= idx_i3:
                active_channel = "Bullish Extension Zone (> 0.618)"
                idx_target_str = f"R1 Extension ({idx_levels.get('i2', 0):.2f})"
            elif idx_i5 <= spot_price < idx_i3:
                active_channel = "Bullish-Neutral Zone (0.500 - 0.618)"
                if spot_price >= idx_mid_3_5:
                    idx_target_str = f"0.618 Resistance ({idx_i3:.2f}) [Above 50% Midpoint 🟢]"
                else:
                    idx_target_str = f"0.500 Support ({idx_i5:.2f}) [Below 50% Midpoint 🔴]"
            elif idx_i6 <= spot_price < idx_i5:
                active_channel = "Neutral-Bearish Zone (0.382 - 0.500)"
                if spot_price >= idx_mid_5_6:
                    idx_target_str = f"0.500 Resistance ({idx_i5:.2f}) [Above 50% Midpoint 🟢]"
                else:
                    idx_target_str = f"0.382 Support ({idx_i6:.2f}) [Below 50% Midpoint 🔴]"
            elif idx_i7 <= spot_price < idx_i6:
                active_channel = "Bearish Zone (0.236 - 0.382)"
                if spot_price >= idx_mid_6_7:
                    idx_target_str = f"0.382 Resistance ({idx_i6:.2f}) [Above 50% Midpoint 🟢]"
                else:
                    idx_target_str = f"0.236 Support ({idx_i7:.2f}) [Below 50% Midpoint 🔴]"
            else:
                active_channel = "Extreme Bearish Zone (< 0.236)"
                idx_target_str = f"Support Low ({idx_levels.get('i0', 0):.2f})"
                
            # Option status
            opt_i3_status = "ACTIVE 🟢" if ltp >= opt_i3 else "BELOW 🔴"
            opt_i5_status = "ACTIVE 🟢" if ltp >= opt_i5 else "BELOW 🔴"
            opt_i6_status = "ACTIVE 🟢" if ltp >= opt_i6 else "BELOW 🔴"
            opt_i7_status = "ACTIVE 🟢" if ltp >= opt_i7 else "BELOW 🔴"
            
            # Option target based on channel
            if strike['type'] == 'CE':
                if spot_price >= idx_mid_6_7:
                    opt_target_str = f"GVN Level 7 / 0.7 ({opt_i7:.2f}) or 0.6 ({opt_i6:.2f}) [Bounce Play]"
                else:
                    opt_target_str = f"Below Level 7 (Under pressure)"
            else: # PE
                if spot_price < idx_mid_5_6:
                    opt_target_str = f"GVN 0.2 Target ({levels.get('i2', 0):.2f}) [Breakout Play]"
                else:
                    opt_target_str = f"Below Target 1 (Awaiting Crossover)"
            
            # Sentiment indicators
            wind_dir = shared_data.market_pulse.get("wind_direction", "NEUTRAL")
            wind_power = shared_data.market_pulse.get("wind_power", 0.0)
            pcr = shared_data.market_pulse.get("pcr", 1.0)
            sentiment = shared_data.market_pulse.get("sentiment", "NEUTRAL")
            
            # GVN Validity Check (True vs Fake Breakout)
            validation_msg = "VALID DUAL-SYNC 🟢"
            if strike['type'] == 'CE' and ltp >= opt_i5:
                if spot_price < idx_i3:
                    validation_msg = f"🔴 FAKE BREAKOUT 🔴\n      (Option CE >= {opt_i5:.2f} but Nifty Spot {spot_price:.2f} < Index 0.618 Level {idx_i3:.2f})"
            elif strike['type'] == 'PE' and ltp >= opt_i5:
                if spot_price > idx_i5:
                    validation_msg = f"🔴 FAKE BREAKOUT 🔴\n      (Option PE >= {opt_i5:.2f} but Nifty Spot {spot_price:.2f} > Index 0.5 Level {idx_i5:.2f})"

            # RSI 15 Trend Check
            rsi_confirm_str = "RSI CONFIRMED 🟢"
            if strike['type'] == 'CE':
                if opt_rsi < 50.0 or idx_rsi < 50.0:
                    rsi_confirm_str = "RSI UNCONFIRMED 🔴 (CE requires both RSI > 50)"
            elif strike['type'] == 'PE':
                if opt_rsi < 50.0 or idx_rsi > 50.0:
                    rsi_confirm_str = "RSI UNCONFIRMED 🔴 (PE requires PE RSI > 50 & Index RSI < 50)"

            change_title = " | ".join(change_desc)
            
            alert_msg = (
                f"🛡️ <b>GVN DUAL-SYNC LEVEL CROSSOVER</b> 🛡️\n"
                f"📢 <b>Trigger:</b> {change_title}\n"
                f"⏰ Timing: <b>{timing}</b>\n\n"
                f"⚖️ <b>GVN Validation:</b>\n"
                f"   • <b>{validation_msg}</b>\n"
                f"   • <b>{rsi_confirm_str}</b>\n\n"
                f"📊 <b>RSI 15 Trend Check:</b>\n"
                f"   • Nifty Spot RSI 15: <b>{idx_rsi:.2f}</b> ({'BULLISH 🟢' if idx_rsi >= 50 else 'BEARISH 🔴'})\n"
                f"   • Option Premium RSI 15: <b>{opt_rsi:.2f}</b> ({'BULLISH 🟢' if opt_rsi >= 50 else 'BEARISH 🔴'})\n\n"
                f"📍 <b>Main Index ({symbol}):</b>\n"
                f"   • Current Spot: <b>{spot_price:.2f}</b> {idx_trend_icon}\n"
                f"   • Active Zone: <b>{active_channel}</b>\n"
                f"   • Level 5 (0.50): <b>{idx_i5:.2f}</b> ({'ABOVE 🟢' if spot_price >= idx_i5 else 'BELOW 🔴'})\n"
                f"   • Mid 5-6 (0.441): <b>{idx_mid_5_6:.2f}</b> ({'ABOVE 🟢' if spot_price >= idx_mid_5_6 else 'BELOW 🔴'})\n"
                f"   • Level 6 (0.382): <b>{idx_i6:.2f}</b> ({'ABOVE 🟢' if spot_price >= idx_i6 else 'BELOW 🔴'})\n"
                f"   • Mid 6-7 (0.309): <b>{idx_mid_6_7:.2f}</b> ({'ABOVE 🟢' if spot_price >= idx_mid_6_7 else 'BELOW 🔴'})\n"
                f"   • Level 7 (0.236): <b>{idx_i7:.2f}</b> ({'ABOVE 🟢' if spot_price >= idx_i7 else 'BELOW 🔴'})\n"
                f"   • Destination: <b>{idx_target_str}</b>\n\n"
                f"🚀 <b>Option Compare ({strike['strike']} {strike['type']}):</b>\n"
                f"   • Current Premium: <b>₹{ltp:.2f}</b>\n"
                f"   • GVN 0.3 Target: <b>₹{opt_i3:.2f}</b> ({opt_i3_status})\n"
                f"   • GVN 0.5 Level: <b>₹{opt_i5:.2f}</b> ({opt_i5_status})\n"
                f"   • GVN 0.6 Level: <b>₹{opt_i6:.2f}</b> ({opt_i6_status})\n"
                f"   • GVN Mid 6-7: <b>₹{opt_mid_6_7:.2f}</b> ({'ABOVE 🟢' if ltp >= opt_mid_6_7 else 'BELOW 🔴'})\n"
                f"   • GVN Level 7: <b>₹{opt_i7:.2f}</b> ({opt_i7_status})\n"
                f"   • Destination: <b>{opt_target_str}</b>\n\n"
                f"🌪️ <b>Wind:</b> {wind_dir} (Power: {wind_power})\n"
                f"📊 PCR: <b>{pcr:.2f}</b> | Sentiment: <b>{sentiment}</b>"
            )
            
            logger.info(f"[TELEGRAM SYNC ALERT] Sending alert for crossover: {change_title}")
            self.telegram.send_alert(alert_msg)


    def _fetch_closes_from_api(self, symbol, strike=None, opt_type=None):
        import requests
        import nse_option_chain
        from datetime import datetime, timedelta
        import shared_data
        
        try:
            if strike and opt_type:
                symbol_token, exch_seg = nse_option_chain.find_angel_token_and_segment(symbol, strike, opt_type)
            else:
                symbol_token, exch_seg = nse_option_chain.find_angel_index_token(symbol)
                
            if not symbol_token:
                return []
                
            token = nse_option_chain.get_angel_token()
            if not token:
                return []
                
            from_dt = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d 09:15")
            to_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            api_key = shared_data.PERMANENT_CREDENTIALS_BACKUP["angel"]["api_key"]
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": api_key,
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0"
            }
            
            hist_payload = {
                "exchange": exch_seg,
                "symboltoken": symbol_token,
                "interval": "FIVE_MINUTE",
                "fromdate": from_dt,
                "todate": to_dt
            }
            
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/v1/getCandleData"
            resp = requests.post(url, json=hist_payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                rj = resp.json()
                if rj.get("status") and rj.get("data"):
                    candles = rj.get("data")
                    return [float(c[4]) for c in candles]
        except Exception as e:
            logger.error(f"❌ Error fetching closes for {symbol} {strike} {opt_type}: {e}")
            
        return []

    def _compute_rsi(self, prices, period=15):
        if len(prices) < period + 1:
            return 50.0
            
        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff > 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))
                
        # Initial average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Wilder's smoothing
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi


if __name__ == "__main__":
    ai = GVNAiDelta60Engine()
    ai.run_ai_loop()
