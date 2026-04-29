"""
GVN Paper Trading Engine: Simultaneous Virtual Capital Trading
Runs parallel to live trading for strategy validation and backtesting
"""

import logging
from datetime import datetime
from collections import deque
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PaperTradingEngine")


# ───────────────────────────────────────────────────────────────
# VIRTUAL PORTFOLIO MANAGER
# ───────────────────────────────────────────────────────────────

class VirtualPortfolio:
    """Manage virtual capital and trades for paper trading"""
    
    def __init__(self, initial_capital=500000):
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.active_trades = []
        self.closed_trades = []
        self.trade_history = deque(maxlen=100)
        self.daily_pnl = 0.0
    
    def open_trade(self, symbol, strike, option_type, entry_price, target, sl, quantity):
        """Open virtual trade"""
        trade = {
            "id": len(self.active_trades) + 1,
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "entry_price": entry_price,
            "target": target,
            "sl": sl,
            "quantity": quantity,
            "notional_value": entry_price * quantity,
            "status": "OPEN",
            "entry_time": datetime.now().isoformat(),
            "exit_time": None,
            "exit_price": None,
            "pnl": 0.0,
            "pnl_percent": 0.0
        }
        
        self.active_trades.append(trade)
        logger.info(f"📝 Virtual Trade Opened: {symbol} {strike}{option_type} @ {entry_price}")
        return trade
    
    def close_trade(self, trade_id, exit_price, exit_reason="MANUAL"):
        """Close virtual trade and calculate P&L"""
        trade = next((t for t in self.active_trades if t["id"] == trade_id), None)
        if not trade:
            logger.warning(f"⚠️ Trade {trade_id} not found")
            return None
        
        # Calculate P&L
        pnl = (exit_price - trade["entry_price"]) * trade["quantity"]
        pnl_percent = (pnl / trade["notional_value"] * 100) if trade["notional_value"] > 0 else 0
        
        # Update trade
        trade["exit_price"] = exit_price
        trade["exit_time"] = datetime.now().isoformat()
        trade["pnl"] = round(pnl, 2)
        trade["pnl_percent"] = round(pnl_percent, 2)
        trade["status"] = "CLOSED"
        trade["exit_reason"] = exit_reason
        
        # Move to closed trades
        self.active_trades.remove(trade)
        self.closed_trades.append(trade)
        self.trade_history.append(trade)
        
        # Update balance and daily P&L
        self.current_balance += pnl
        self.daily_pnl += pnl
        
        status_emoji = "✅" if pnl > 0 else "❌"
        logger.info(f"{status_emoji} Virtual Trade Closed: {trade['symbol']} | P&L: {pnl}")
        
        return trade
    
    def update_trade_marked_to_market(self, trade_id, current_price):
        """Update unrealized P&L for open trades"""
        trade = next((t for t in self.active_trades if t["id"] == trade_id), None)
        if not trade:
            return None
        
        unrealized_pnl = (current_price - trade["entry_price"]) * trade["quantity"]
        trade["unrealized_pnl"] = round(unrealized_pnl, 2)
        trade["unrealized_pnl_percent"] = round((unrealized_pnl / trade["notional_value"] * 100), 2) if trade["notional_value"] > 0 else 0
        
        return trade
    
    def get_portfolio_stats(self):
        """Get complete portfolio statistics"""
        total_trades = len(self.closed_trades)
        winning_trades = len([t for t in self.closed_trades if t["pnl"] > 0])
        losing_trades = len([t for t in self.closed_trades if t["pnl"] < 0])
        total_pnl = sum(t.get("pnl", 0) for t in self.closed_trades)
        avg_win = sum(t.get("pnl", 0) for t in self.closed_trades if t["pnl"] > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(t.get("pnl", 0) for t in self.closed_trades if t["pnl"] < 0) / losing_trades if losing_trades > 0 else 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        unrealized_pnl = sum(t.get("unrealized_pnl", 0) for t in self.active_trades)
        
        return {
            "initial_capital": self.initial_capital,
            "current_balance": round(self.current_balance, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round((total_pnl / self.initial_capital * 100), 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
            "active_trades": len(self.active_trades)
        }
    
    def reset_daily(self):
        """Reset daily stats (called at market close)"""
        self.daily_pnl = 0.0
        logger.info("📊 Daily stats reset for next trading day")


# ───────────────────────────────────────────────────────────────
# PAPER TRADING EXECUTOR
# ───────────────────────────────────────────────────────────────

class PaperTradingExecutor:
    """Execute paper trades in parallel with live trading"""
    
    def __init__(self, initial_capital=500000):
        self.portfolio = VirtualPortfolio(initial_capital)
        self.trade_counter = 0
        self.performance_log = []
    
    def execute_paper_buy(self, symbol, strike, option_type, entry_price, target, sl, quantity):
        """Execute virtual buy order"""
        trade = self.portfolio.open_trade(
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            entry_price=entry_price,
            target=target,
            sl=sl,
            quantity=quantity
        )
        
        self.trade_counter += 1
        self.performance_log.append({
            "type": "BUY",
            "timestamp": datetime.now().isoformat(),
            "trade": trade
        })
        
        return trade
    
    def execute_paper_sell(self, trade_id, exit_price, exit_reason="TARGET_HIT"):
        """Execute virtual sell order"""
        trade = self.portfolio.close_trade(trade_id, exit_price, exit_reason)
        
        if trade:
            self.performance_log.append({
                "type": "SELL",
                "timestamp": datetime.now().isoformat(),
                "trade": trade
            })
        
        return trade
    
    def get_daily_report(self):
        """Generate daily paper trading report"""
        stats = self.portfolio.get_portfolio_stats()
        
        report = f"""
┌─────────────────────────────────────────────────────────────┐
│         GVN PAPER TRADING DAILY REPORT                      │
├─────────────────────────────────────────────────────────────┤
│ Initial Capital:      ₹{stats['initial_capital']:,}
│ Current Balance:      ₹{stats['current_balance']:,}
│ Total P&L:            {stats['total_pnl']:+.2f} pts ({stats['total_pnl_percent']:+.2f}%)
│ Daily P&L:            {stats['daily_pnl']:+.2f} pts
│─────────────────────────────────────────────────────────────│
│ Total Trades:         {stats['total_trades']}
│ Winning Trades:       {stats['winning_trades']} ({stats['win_rate']:.1f}%)
│ Losing Trades:        {stats['losing_trades']}
│ Avg Win/Loss Ratio:   {stats['profit_factor']:.2f}x
│─────────────────────────────────────────────────────────────│
│ Active Trades:        {stats['active_trades']}
│ Unrealized P&L:       {stats['unrealized_pnl']:+.2f} pts
└─────────────────────────────────────────────────────────────┘
"""
        return report
    
    def get_performance_metrics(self):
        """Get comprehensive performance metrics"""
        stats = self.portfolio.get_portfolio_stats()
        return stats
    
    def sync_with_live_trade(self, live_trade_info):
        """Synchronize paper trade with live trade execution"""
        """This ensures paper trading mirrors live trading exactly"""
        virtual_trade = self.execute_paper_buy(
            symbol=live_trade_info.get("symbol"),
            strike=live_trade_info.get("strike"),
            option_type=live_trade_info.get("option_type"),
            entry_price=live_trade_info.get("entry_price"),
            target=live_trade_info.get("target"),
            sl=live_trade_info.get("sl"),
            quantity=live_trade_info.get("quantity")
        )
        
        logger.info(f"📋 Paper trade synced with live: {live_trade_info.get('symbol')}")
        return virtual_trade


# ───────────────────────────────────────────────────────────────
# PAPER TRADING MANAGER (Global)
# ───────────────────────────────────────────────────────────────

class PaperTradingManager:
    """Global paper trading manager for the entire system"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.executor = PaperTradingExecutor(initial_capital=500000)
        return cls._instance
    
    def get_executor(self):
        return self.executor
    
    def get_current_stats(self):
        return self.executor.get_performance_metrics()
    
    def get_daily_report(self):
        return self.executor.get_daily_report()


# ───────────────────────────────────────────────────────────────
# TEST / INITIALIZATION
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Initialize
    executor = PaperTradingExecutor(initial_capital=500000)
    
    # Simulate trades
    print("✅ Paper Trading Engine Initialized")
    print(f"Initial Capital: ₹500,000")
    
    # Open trade 1
    trade1 = executor.execute_paper_buy(
        symbol="NIFTY",
        strike="25000",
        option_type="CE",
        entry_price=100,
        target=120,
        sl=80,
        quantity=65
    )
    
    # Close trade 1 (winner)
    executor.execute_paper_sell(trade1["id"], exit_price=120, exit_reason="TARGET_HIT")
    
    # Open trade 2
    trade2 = executor.execute_paper_buy(
        symbol="NIFTY",
        strike="25100",
        option_type="CE",
        entry_price=80,
        target=100,
        sl=60,
        quantity=65
    )
    
    # Close trade 2 (loser)
    executor.execute_paper_sell(trade2["id"], exit_price=70, exit_reason="SL_HIT")
    
    # Print report
    print(executor.get_daily_report())
