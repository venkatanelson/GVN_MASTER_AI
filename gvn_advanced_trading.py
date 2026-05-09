"""
Advanced Auto-Trading Module - Position Management
Pyramid Entry, Trailing Stops, Risk Management, Smart Sizing
"""

import logging
from datetime import datetime
import shared_data
import gvn_levels_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AdvancedTrading")

class AdvancedPositionManager:
    """
    Manages advanced trading features:
    - Pyramid entry (add to winners)
    - Trailing stop losses
    - Risk limits
    - Position sizing
    """
    
    def __init__(self):
        self.pyramid_settings = {
            "enabled": True,
            "max_pyramid_levels": 3,  # Max 3 positions per symbol
            "pyramid_on_profit_pct": 2.0,  # Add when +2% profit
            "scale_up_qty_multiplier": 0.5,  # 50% of initial qty for 2nd position
            "min_profit_to_pyramid": 15,  # Min 15 points profit to add
        }
        
        self.trailing_stop_settings = {
            "enabled": True,
            "trail_by_pct": 1.5,  # Trail stop 1.5% below high
            "activate_after_pct_gain": 1.0,  # Activate trailing stop after 1% gain
        }
        
        self.risk_management = {
            "max_daily_loss": -5000,  # Stop trading if -5000 loss
            "max_open_positions": 3,  # Max 3 concurrent trades
            "max_loss_per_trade": -500,  # Exit if single trade loses 500
            "risk_reward_ratio_min": 1.5,  # Target must be 1.5x risk
        }
        
        self.position_sizing = {
            "dynamic_sizing": True,
            "base_qty": 1,
            "atr_period": 14,  # For volatility calculation
            "risk_per_trade_pct": 1.0,  # Risk 1% per trade
        }
        
        self.pyramid_tracker = {}  # {symbol: [position1, position2, ...]}
        self.highest_price = {}  # {symbol: highest_price_since_entry}
        self.trade_details = {}  # Enhanced trade tracking

    # ═════════════════════════════════════════════════════════════
    # PYRAMID ENTRY SYSTEM
    # ═════════════════════════════════════════════════════════════
    
    def check_pyramid_opportunity(self, symbol, current_price, entry_price):
        """
        Check if we should add to position (pyramid)
        Conditions:
        - Trade is profitable (>min_profit_to_pyramid)
        - Haven't reached max_pyramid_levels
        - Price is making higher high
        """
        if not self.pyramid_settings["enabled"]:
            return False, 0
        
        try:
            # Calculate current profit
            profit_pts = current_price - entry_price
            profit_pct = (profit_pts / entry_price) * 100
            
            # Get pyramid count for this symbol
            pyramid_count = len(self.pyramid_tracker.get(symbol, []))
            
            # Condition 1: Enough profit
            if profit_pts < self.pyramid_settings["min_profit_to_pyramid"]:
                logger.debug(f"  Pyramid blocked for {symbol}: Only +{profit_pts} pts (need +{self.pyramid_settings['min_profit_to_pyramid']})")
                return False, 0
            
            # Condition 2: Haven't exceeded max levels
            if pyramid_count >= self.pyramid_settings["max_pyramid_levels"]:
                logger.debug(f"  Pyramid blocked for {symbol}: Already at max {pyramid_count} levels")
                return False, 0
            
            # Condition 3: Profit threshold reached
            if profit_pct < self.pyramid_settings["pyramid_on_profit_pct"]:
                logger.debug(f"  Pyramid blocked for {symbol}: Only +{profit_pct:.2f}% (need +{self.pyramid_settings['pyramid_on_profit_pct']}%)")
                return False, 0
            
            # All conditions met
            add_qty = int(self.pyramid_settings["scale_up_qty_multiplier"] * pyramid_count + 1)
            
            logger.info(f"✅ PYRAMID OPPORTUNITY: {symbol}")
            logger.info(f"   Current Profit: +{profit_pct:.2f}% ({profit_pts:.2f} pts)")
            logger.info(f"   Adding Level {pyramid_count + 1}: {add_qty} qty @ {current_price}")
            
            return True, add_qty
        
        except Exception as e:
            logger.error(f"Error checking pyramid: {e}")
            return False, 0

    def execute_pyramid_entry(self, symbol, qty, entry_price):
        """
        Add position to pyramid tracker
        """
        try:
            if symbol not in self.pyramid_tracker:
                self.pyramid_tracker[symbol] = []
            
            position = {
                "entry_price": entry_price,
                "qty": qty,
                "entry_time": datetime.now(),
                "level": len(self.pyramid_tracker[symbol]) + 1,
                "status": "ACTIVE"
            }
            
            self.pyramid_tracker[symbol].append(position)
            
            logger.info(f"🔺 [PYRAMID] Added Level {position['level']} for {symbol}: {qty}@{entry_price}")
            
            return True
        except Exception as e:
            logger.error(f"Error executing pyramid: {e}")
            return False

    def get_pyramid_status(self, symbol):
        """Get current pyramid position info"""
        positions = self.pyramid_tracker.get(symbol, [])
        
        total_qty = sum(p["qty"] for p in positions)
        avg_entry = sum(p["entry_price"] * p["qty"] for p in positions) / total_qty if total_qty > 0 else 0
        
        return {
            "symbol": symbol,
            "levels": len(positions),
            "total_qty": total_qty,
            "avg_entry": avg_entry,
            "positions": positions
        }

    # ═════════════════════════════════════════════════════════════
    # TRAILING STOP LOSS SYSTEM
    # ═════════════════════════════════════════════════════════════
    
    def update_trailing_stop(self, symbol, current_price, entry_price):
        """
        Update highest price and calculate trailing stop
        """
        try:
            if symbol not in self.highest_price:
                self.highest_price[symbol] = entry_price
            
            # Update highest price
            if current_price > self.highest_price[symbol]:
                self.highest_price[symbol] = current_price
                logger.debug(f"  {symbol} new high: {current_price}")
            
            current_high = self.highest_price[symbol]
            profit_pct = ((current_high - entry_price) / entry_price) * 100
            
            # Check if we should activate trailing stop
            if profit_pct < self.trailing_stop_settings["activate_after_pct_gain"]:
                return None  # Trailing stop not active yet
            
            # Calculate trailing stop level
            trail_pct = self.trailing_stop_settings["trail_by_pct"]
            trailing_sl = current_high - (current_high * trail_pct / 100)
            
            logger.debug(f"  {symbol} trailing SL: {trailing_sl:.2f} (High: {current_high}, Trail: {trail_pct}%)")
            
            return trailing_sl
        
        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return None

    def should_exit_on_trailing_stop(self, symbol, current_price, entry_price):
        """
        Check if price hit trailing stop loss
        """
        trailing_sl = self.update_trailing_stop(symbol, current_price, entry_price)
        
        if trailing_sl is None:
            return False, None
        
        if current_price <= trailing_sl:
            logger.info(f"🛑 [TRAILING STOP HIT] {symbol} @ {current_price} (SL: {trailing_sl:.2f})")
            return True, trailing_sl
        
        return False, trailing_sl

    # ═════════════════════════════════════════════════════════════
    # RISK MANAGEMENT SYSTEM
    # ═════════════════════════════════════════════════════════════
    
    def check_risk_limits(self):
        """
        Check portfolio-level risk constraints
        Returns: (is_ok, reason)
        """
        try:
            stats = shared_data.get_trade_stats()
            daily_pnl = stats['total_pnl']
            
            # Check daily loss limit
            if daily_pnl <= self.risk_management["max_daily_loss"]:
                logger.error(f"⛔ DAILY LOSS LIMIT HIT: {daily_pnl:.2f} <= {self.risk_management['max_daily_loss']}")
                return False, "Daily loss limit exceeded"
            
            # Check max open positions
            open_count = len(shared_data.active_trades.get("NIFTY", []))
            open_count += len(shared_data.active_trades.get("BANKNIFTY", []))
            open_count += len(shared_data.active_trades.get("FINNIFTY", []))
            
            if open_count >= self.risk_management["max_open_positions"]:
                logger.warning(f"⚠️  Max positions reached: {open_count}/{self.risk_management['max_open_positions']}")
                return False, "Max open positions reached"
            
            return True, "Risk limits OK"
        
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return True, "Risk check passed"

    def validate_risk_reward(self, entry_price, sl_price, target_price):
        """
        Validate risk:reward ratio is acceptable
        """
        try:
            risk = abs(entry_price - sl_price)
            reward = abs(target_price - entry_price)
            
            if risk == 0:
                return False
            
            ratio = reward / risk
            min_ratio = self.risk_management["risk_reward_ratio_min"]
            
            if ratio < min_ratio:
                logger.warning(f"⚠️  Poor R:R ratio: {ratio:.2f} < {min_ratio}")
                return False
            
            logger.info(f"✓ Risk:Reward ratio: {ratio:.2f}x (target: {target_price}, SL: {sl_price})")
            return True
        
        except Exception as e:
            logger.error(f"Error validating R:R: {e}")
            return False

    # ═════════════════════════════════════════════════════════════
    # SMART POSITION SIZING
    # ═════════════════════════════════════════════════════════════
    
    def calculate_dynamic_position_size(self, symbol, current_price, atr_value=None):
        """
        Calculate position size based on volatility
        Formula: Qty = (Account Risk Pct) / (2 * ATR)
        """
        try:
            if not self.position_sizing["dynamic_sizing"]:
                return self.position_sizing["base_qty"]
            
            # If ATR not provided, use fixed size
            if atr_value is None or atr_value == 0:
                logger.debug(f"  Using base qty: {self.position_sizing['base_qty']}")
                return self.position_sizing["base_qty"]
            
            # Get account size (from trade history if available)
            stats = shared_data.get_trade_stats()
            account_size = 100000  # Default 1L account (configurable)
            
            # Calculate risk amount
            risk_amount = account_size * (self.position_sizing["risk_per_trade_pct"] / 100)
            
            # Position size = Risk Amount / (2 * ATR)
            # 2 * ATR = typical stop loss distance
            position_size = risk_amount / (2 * atr_value)
            position_size = max(1, int(position_size))  # Minimum 1 lot
            
            logger.info(f"📊 Dynamic Size for {symbol}:")
            logger.info(f"   ATR: {atr_value:.2f}")
            logger.info(f"   Risk: {risk_amount:.0f} ({self.position_sizing['risk_per_trade_pct']}%)")
            logger.info(f"   Qty: {position_size}")
            
            return position_size
        
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.position_sizing["base_qty"]

    # ═════════════════════════════════════════════════════════════
    # PERFORMANCE ANALYTICS
    # ═════════════════════════════════════════════════════════════
    
    def get_session_analytics(self):
        """
        Get comprehensive session performance metrics
        """
        try:
            stats = shared_data.get_trade_stats()
            
            total_trades = stats['total_trades']
            win_rate = (stats['winning_trades'] / total_trades * 100) if total_trades > 0 else 0
            avg_win = 0
            avg_loss = 0
            
            if total_trades > 0:
                trades = stats['trades']
                wins = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0]
                losses = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]
                
                avg_win = sum(wins) / len(wins) if wins else 0
                avg_loss = abs(sum(losses) / len(losses)) if losses else 0
            
            # Calculate profit factor
            profit_factor = (stats['winning_trades'] * avg_win) / (stats['losing_trades'] * avg_loss) if avg_loss > 0 else 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": stats['winning_trades'],
                "losing_trades": stats['losing_trades'],
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "total_pnl": stats['total_pnl'],
                "max_consecutive_wins": self._get_max_streak(stats['trades'], True),
                "max_consecutive_losses": self._get_max_streak(stats['trades'], False),
            }
        
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}

    def _get_max_streak(self, trades, is_winning):
        """Calculate max winning/losing streak"""
        if not trades:
            return 0
        
        max_streak = 0
        current_streak = 0
        
        for trade in trades:
            is_winner = trade.get('pnl', 0) > 0
            
            if (is_winning and is_winner) or (not is_winning and not is_winner):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak

    # ═════════════════════════════════════════════════════════════
    # CONFIGURATION & STATUS
    # ═════════════════════════════════════════════════════════════
    
    def get_advanced_status(self):
        """Get full advanced trading status"""
        return {
            "pyramid": {
                "enabled": self.pyramid_settings["enabled"],
                "current_pyramids": len(self.pyramid_tracker),
                "max_levels": self.pyramid_settings["max_pyramid_levels"]
            },
            "trailing_stops": {
                "enabled": self.trailing_stop_settings["enabled"],
                "tracked_symbols": len(self.highest_price)
            },
            "risk_mgmt": {
                "daily_loss_limit": self.risk_management["max_daily_loss"],
                "max_positions": self.risk_management["max_open_positions"],
                "risk_reward_ratio": self.risk_management["risk_reward_ratio_min"]
            },
            "position_sizing": {
                "dynamic": self.position_sizing["dynamic_sizing"],
                "risk_per_trade": self.position_sizing["risk_per_trade_pct"]
            },
            "performance": self.get_session_analytics()
        }

    def configure_pyramid(self, **kwargs):
        """Reconfigure pyramid settings"""
        self.pyramid_settings.update(kwargs)
        logger.info(f"✓ Pyramid settings updated: {kwargs}")

    def configure_trailing_stops(self, **kwargs):
        """Reconfigure trailing stop settings"""
        self.trailing_stop_settings.update(kwargs)
        logger.info(f"✓ Trailing stop settings updated: {kwargs}")

    def configure_risk_management(self, **kwargs):
        """Reconfigure risk management"""
        self.risk_management.update(kwargs)
        logger.info(f"✓ Risk management updated: {kwargs}")

    def configure_position_sizing(self, **kwargs):
        """Reconfigure position sizing"""
        self.position_sizing.update(kwargs)
        logger.info(f"✓ Position sizing updated: {kwargs}")

# Global instance
advanced_trader = None

def get_advanced_trader():
    """Get or create advanced trader instance"""
    global advanced_trader
    if advanced_trader is None:
        advanced_trader = AdvancedPositionManager()
    return advanced_trader
