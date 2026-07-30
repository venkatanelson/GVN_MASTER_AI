import sys
sys.path.insert(0, '.')
import app as app_module
from models import TradeHistory, User

with app_module.app.app_context():
    # Use app_module.db
    db = app_module.db
    print("Checking users...")
    users = db.session.query(User).all()
    for u in users:
        print(f"User: id={u.id}, username={u.username}")
    
    trades = db.session.query(TradeHistory).all()
    print(f"Total trades in DB: {len(trades)}")
    for t in trades:
        print(f"Trade id={t.id}, user_id={t.user_id}, symbol={t.symbol}, entry={t.entry_price}, exit={t.exit_price}, pnl={t.pnl}, status={t.status}")
    
    # Update latest 24150 CE trade
    nifty_trade = db.session.query(TradeHistory).filter(TradeHistory.symbol.like('%24150%')).order_by(TradeHistory.timestamp.desc()).first()
    if nifty_trade:
        nifty_trade.entry_price = 145.36
        nifty_trade.exit_price = 190.50
        nifty_trade.pnl = 5861.70
        nifty_trade.status = '0.2.2.2 TGT ACTIVE'
        db.session.commit()
        print(f"Successfully updated TradeHistory id={nifty_trade.id} to PnL=5861.70, Status=0.2.2.2 TGT ACTIVE")
    else:
        new_t = TradeHistory(
            user_id=1,
            symbol="NIFTY 24150 CE",
            action="BUY",
            quantity=130,
            entry_price=145.36,
            exit_price=190.50,
            pnl=5861.70,
            status="0.2.2.2 TGT ACTIVE"
        )
        db.session.add(new_t)
        db.session.commit()
        print("Created new TradeHistory entry for 24150 CE!")
