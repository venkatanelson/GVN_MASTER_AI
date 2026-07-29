import time
import datetime
import shared_data
import gvn_alpha_engine
import gvn_levels_engine
import gvn_delta_levels_engine
import broker_api
import nse_option_chain
import gvn_advanced_trading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVNMasterRobot")

class GVNMasterRobot:
    def __init__(self):
        self.priority_delta_min = 0.59
        self.priority_delta_max = 0.69
        self.stop_loss_pts = 20 # USER REQUEST: minimum 20 points stop loss
        self.panic_exit_pts = 25
        self.active_trades = {} # {symbol: trade_info}
        self.last_processed_time = None
        self.strike_level_cache = {} # Cache GVN levels for strikes
        self.market_indices = ["NIFTY", "SENSEX"]
        self.is_running = False
        
        # Initialize advanced trading module
        self.advanced_trader = gvn_advanced_trading.get_advanced_trader()
        logger.info("🚀 [ROBOT] Advanced trading initialized (Pyramid, Trailing Stops, Risk Management)")

    def run_robot_cycle(self):
        """
        The main loop for the GVN Master Robot.
        Checks levels, delta, and triggers trades.
        """
        self.is_running = True
        logger.info("🤖 [MASTER ROBOT] Starting main cycle...")
        
        while self.is_running:
            try:
                current_time = datetime.datetime.now()
                
                # Only run during market hours (9:15 AM - 3:30 PM IST)
                if not self._is_market_hours(current_time):
                    time.sleep(30)
                    continue
                
                # 1. Get Priority Strikes (Delta 0.59-0.69)
                priority_strikes = self.get_priority_strikes()
                
                if not priority_strikes:
                    logger.debug("No priority strikes found")
                    time.sleep(5)
                    continue
                
                logger.info(f"📊 [ROBOT] Found {len(priority_strikes)} priority strikes")
                
                for strike in priority_strikes:
                    try:
                        # 🎯 GVN SCANNER: Only execute trades if this is the active dashboard symbol
                        index_name = strike.get('index', '').upper()
                        active_index = getattr(shared_data, 'active_dashboard_symbol', 'NIFTY').upper()
                        if index_name != active_index:
                            continue

                        symbol = strike['symbol']
                        ltp = strike.get('ltp', 0)
                        delta = strike.get('delta', 0)
                        option_type = strike.get('option_type', '')

                        # 🌟 GVN SPECIAL: Index 9:15 Candle Closing Bias Filter 🌟
                        benchmark = shared_data.gvn_915_benchmark.get(index_name)
                        if benchmark and benchmark.get("captured") and benchmark.get("date") == datetime.datetime.now().strftime("%Y-%m-%d"):
                            high_915 = benchmark.get("high", 0)
                            low_915 = benchmark.get("low", 0)
                            close_915 = benchmark.get("close", 0)
                            
                            # Calculate index GVN levels
                            index_levels = gvn_levels_engine.calculate_gvn_levels(high_915, low_915, close_915)
                            if index_levels and "i5" in index_levels and close_915 > 0:
                                i5_level = index_levels["i5"]
                                if close_915 >= i5_level:
                                    market_bias = "CE"
                                    bias_reason = f"Index 9:15 close ({close_915}) >= i5 level ({i5_level}) -> CALL SIDE BIAS"
                                else:
                                    market_bias = "PE"
                                    bias_reason = f"Index 9:15 close ({close_915}) < i5 level ({i5_level}) -> PUT SIDE BIAS"
                                
                                # Log bias observation to AI memory if not logged yet for today
                                if not hasattr(shared_data, "logged_today_bias") or shared_data.logged_today_bias != benchmark.get("date"):
                                    observation = {
                                        "timestamp": datetime.datetime.now().isoformat(),
                                        "index": index_name,
                                        "high_915": high_915,
                                        "low_915": low_915,
                                        "close_915": close_915,
                                        "i5_level": i5_level,
                                        "bias": market_bias,
                                        "reason": bias_reason
                                    }
                                    shared_data.append_ai_memory(observation)
                                    shared_data.logged_today_bias = benchmark.get("date")
                                    logger.info(f"🧠 [AI MEMORY] Saved today's bias: {bias_reason}")
                                
                                # Apply filter: block opposite side trades
                                if option_type != market_bias:
                                    continue
                        
                        # 2. Get GVN Master Levels (5m 9:15 base)
                        levels = self.strike_level_cache.get(symbol)
                        if not levels:
                            # Calculate if missing
                            levels = self._fetch_and_calc_levels(symbol, strike)
                            if levels:
                                self.strike_level_cache[symbol] = levels
                        
                        if not levels:
                            continue
                        
                        # 3. Check if price triggers any level (i0-i7)
                        triggered_level = self._check_level_trigger(symbol, ltp, levels)
                        
                        if triggered_level and symbol not in self.active_trades:
                            # 4. Execute trade if conditions met
                            self.execute_trade(symbol, triggered_level, ltp, delta, levels)
                    
                    except Exception as e:
                        logger.error(f"Error processing strike {strike.get('symbol', 'UNKNOWN')}: {e}")
                        continue
                
                # 5. Monitor Active Trades for SL/Targets
                self.manage_active_trades()
                
                time.sleep(1) # High frequency monitoring
            except Exception as e:
                logger.error(f"[MASTER ROBOT ERROR] {e}")
                time.sleep(5)

    def get_priority_strikes(self):
        """
        Filters option chain for strikes with Delta between 0.59-0.69.
        Returns list of strike data with symbol, LTP, delta, high, low.
        """
        priority_strikes = []
        
        try:
            # Get latest option chain from NSE
            for index in self.market_indices:
                option_chain = nse_option_chain.get_option_chain(index)
                
                if not option_chain:
                    continue
                
                # Filter CE and PE strikes by delta range
                for option_type in ["CE", "PE"]:
                    for strike in option_chain.get(option_type, []):
                        delta = strike.get('delta', 0)
                        
                        # Check if delta is in priority range
                        if self.priority_delta_min <= delta <= self.priority_delta_max:
                            priority_strikes.append({
                                'symbol': f"{index}{strike.get('strike', '')}",
                                'index': index,
                                'option_type': option_type,
                                'strike': strike.get('strike'),
                                'ltp': strike.get('ltp', 0),
                                'delta': delta,
                                'high_915': strike.get('high_915', 0),
                                'low_915': strike.get('low_915', 0),
                                'volume': strike.get('volume', 0),
                                'open_interest': strike.get('open_interest', 0),
                                'expiry': strike.get('expiry', '')
                            })
        except Exception as e:
            logger.error(f"Error fetching priority strikes: {e}")
        
        return priority_strikes

    def _fetch_and_calc_levels(self, symbol, strike_data):
        """
        Fetches high/low from 9:15 AM candle and calculates GVN levels.
        """
        try:
            high_915 = strike_data.get('high_915', 0)
            low_915 = strike_data.get('low_915', 0)
            
            if high_915 and low_915:
                levels = gvn_levels_engine.calculate_gvn_levels(high_915, low_915)
                return levels
        except Exception as e:
            logger.error(f"Error calculating levels for {symbol}: {e}")
        
        return None

    def _check_level_trigger(self, symbol, ltp, levels):
        """
        Checks if current LTP triggers any GVN level (i0, i1, i2, i3, i5, i6, i7).
        Returns the triggered level type or None.
        Tolerance: ±0.25 points for high precision.
        """
        tolerance = 0.25
        
        for level_key in ['i0', 'i1', 'i2', 'i3', 'i5', 'i6', 'i7']:
            level_price = levels.get(level_key, 0)
            
            if level_price > 0 and abs(ltp - level_price) <= tolerance:
                logger.info(f"⚡ [TRIGGER] {symbol} triggered level {level_key} @ {ltp} (Level: {level_price})")
                return {
                    'level': level_key,
                    'price': level_price,
                    'entry': ltp
                }
        
        return None

    def execute_trade(self, symbol, trigger_info, ltp, delta, levels):
        """
        Executes a trade when a level is triggered.
        """
        try:
            level_key = trigger_info['level']
            # Use exact GVN level trigger price if available, otherwise ltp
            entry_price = trigger_info.get('price', ltp)
            sl_price = round(entry_price - self.stop_loss_pts, 2)
            
            # Calculate targets based on triggered level
            targets = self._calculate_targets(entry_price, levels)
            
            logger.info(f"🚀 [ROBOT] Executing LONG for {symbol} @ {entry_price} (Delta: {delta}, Level: {level_key})")
            logger.info(f"   SL: {sl_price}, Targets: {targets}")
            
            # Execute via broker API
            order_id = broker_api.place_order_universal(
                cfg={},  # Would have broker config in production
                symbol=symbol,
                txn_type="BUY",
                qty=1
            )
            
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            # Track active trade
            self.active_trades[symbol] = {
                "order_id": order_id,
                "entry_price": entry_price,
                "entry_time": datetime.datetime.now(ist_tz),
                "sl": sl_price,
                "targets": targets,
                "triggered_level": level_key,
                "delta": delta,
                "status": "ACTIVE"
            }
            
            logger.info(f"✅ Order placed: {order_id}")
        
        except Exception as e:
            logger.error(f"Error executing trade for {symbol}: {e}")

    def manage_active_trades(self):
        """
        Monitors active trades and exits on SL hit or target hit.
        Also handles pyramid entries and trailing stops.
        """
        # First, check risk limits
        risk_ok, risk_reason = self.advanced_trader.check_risk_limits()
        if not risk_ok:
            logger.warning(f"⛔ {risk_reason} - No new pyramid entries allowed")
        
        trades_to_remove = []
        
        for symbol, trade_info in self.active_trades.items():
            try:
                # Get current LTP
                current_ltp = nse_option_chain.get_current_ltp(symbol)
                
                if not current_ltp or current_ltp == 0:
                    continue
                
                entry_price = trade_info['entry_price']
                sl = trade_info['sl']
                targets = trade_info['targets']
                
                # ═════ ADVANCED: Check Trailing Stop ═════
                should_exit_trail, trailing_sl = self.advanced_trader.should_exit_on_trailing_stop(
                    symbol, current_ltp, entry_price
                )
                
                if should_exit_trail:
                    self._close_trade(symbol, current_ltp, "TRAILING_STOP_HIT")
                    trades_to_remove.append(symbol)
                    continue
                
                # ═════ ADVANCED: Check Pyramid Opportunity ═════
                if risk_ok:
                    pyramid_enabled, add_qty = self.advanced_trader.check_pyramid_opportunity(
                        symbol, current_ltp, entry_price
                    )
                    
                    if pyramid_enabled:
                        # Execute pyramid entry
                        self.advanced_trader.execute_pyramid_entry(symbol, add_qty, current_ltp)
                        logger.info(f"🔺 [PYRAMID] Added {add_qty} qty to {symbol}")
                
                # ═════ STANDARD: Check SL hit
                if current_ltp <= sl:
                    logger.warning(f"🛑 [SL HIT] {symbol} @ {current_ltp} (SL: {sl})")
                    self._close_trade(symbol, current_ltp, "SL_HIT")
                    trades_to_remove.append(symbol)
                
                # Check target hit
                elif any(current_ltp >= target for target in targets):
                    hit_target = next((t for t in targets if current_ltp >= t), None)
                    logger.info(f"🎯 [TARGET HIT] {symbol} @ {current_ltp} (Target: {hit_target})")
                    self._close_trade(symbol, current_ltp, "TARGET_HIT")
                    trades_to_remove.append(symbol)
                
                # Check panic exit (16 points loss)
                elif current_ltp <= entry_price - self.panic_exit_pts:
                    logger.warning(f"🔴 [PANIC EXIT] {symbol} @ {current_ltp}")
                    self._close_trade(symbol, current_ltp, "PANIC_EXIT")
                    trades_to_remove.append(symbol)
            
            except Exception as e:
                logger.error(f"Error managing trade {symbol}: {e}")
        
        # Remove closed trades
        for symbol in trades_to_remove:
            del self.active_trades[symbol]

    def _close_trade(self, symbol, exit_price, exit_reason):
        """
        Closes a trade and logs exit information.
        """
        try:
            trade_info = self.active_trades.get(symbol)
            if not trade_info:
                return
            
            entry_price = trade_info['entry_price']
            pnl = exit_price - entry_price
            pnl_pct = (pnl / entry_price * 100) if entry_price > 0 else 0
            
            logger.info(f"📊 [TRADE CLOSED] {symbol} | Entry: {entry_price} | Exit: {exit_price} | PnL: {pnl} ({pnl_pct:.2f}%) | Reason: {exit_reason}")
            
            # Execute exit order via broker
            broker_api.place_order_universal(
                cfg={},
                symbol=symbol,
                txn_type="SELL",
                qty=1
            )
        
        except Exception as e:
            logger.error(f"Error closing trade {symbol}: {e}")

    def _calculate_targets(self, entry_price, levels):
        """
        Calculates profit targets strictly based on exact GVN levels (i5, i3, i2, etc.).
        E.g., Entry at i6 (319.32) -> Target 1 at i5 (389.82), Target 2 at i3 (460.31).
        """
        targets = []
        if isinstance(levels, dict):
            # Extract all GVN level prices above entry_price
            valid_higher_levels = [
                round(float(price), 2) for key, price in levels.items()
                if isinstance(price, (int, float)) and price > entry_price + 0.5
            ]
            targets = sorted(list(set(valid_higher_levels)))
        
        # Fallback if specific GVN levels higher than entry are unavailable
        if len(targets) == 0:
            targets.append(round(entry_price + 70.5, 2))  # Approx ~0.50 level jump
            targets.append(round(entry_price + 141.0, 2)) # Approx ~0.30 level jump
        elif len(targets) == 1:
            targets.append(round(targets[0] + 70.5, 2))
        
        logger.info(f"🎯 [GVN TARGETS] Entry: {entry_price} -> GVN Targets: {targets}")
        return targets

    def _is_market_hours(self, dt):
        """
        Checks if current time is within market hours (9:15 AM - 3:30 PM IST).
        """
        if dt.weekday() >= 5:  # Weekend
            return False
        
        market_open = dt.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = dt.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= dt <= market_close

    def stop(self):
        """
        Gracefully stops the robot.
        """
        logger.info("🛑 [MASTER ROBOT] Stopping...")
        self.is_running = False

# Start Robot in Background
def start_master_robot():
    robot = GVNMasterRobot()
    import threading
    robot_thread = threading.Thread(target=robot.run_robot_cycle, daemon=True)
    robot_thread.start()
    return robot
