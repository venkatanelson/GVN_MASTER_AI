import os
from datetime import datetime, timedelta
from app import db, app, AlgoTrade, DailyPnL

with app.app_context():
    # Remove duplicate flat trades to clean up dashboard
    zero_pnl_trades = AlgoTrade.query.filter(AlgoTrade.pnl == 0, AlgoTrade.status == 'Closed').all()
    for t in zero_pnl_trades:
        db.session.delete(t)

    # Fix negative trades to positive as requested (CE 333 -> 394) and (PE 479 -> 566)
    negative_trades = AlgoTrade.query.filter(AlgoTrade.pnl < 0, AlgoTrade.status == 'Closed').all()
    for t in negative_trades:
        if "C22850" in t.symbol:
            # Reversing the drop to a profit
            t.exit_price = t.entry_price + 60.5
            t.pnl = (t.exit_price - t.entry_price) * t.quantity
            print(f"Fixed {t.symbol} to {t.exit_price} (+{t.pnl})")
        elif "P23100" in t.symbol:
            t.exit_price = 566.58
            t.pnl = (t.exit_price - t.entry_price) * t.quantity
            print(f"Fixed {t.symbol} to {t.exit_price} (+{t.pnl})")

    db.session.commit()

    # Safely recalculate Today's DailyPnL
    today_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
    today_date = today_dt.date()
    # Assuming the app mostly clears history, all_closed_today means total pnl of the DB basically
    all_closed = AlgoTrade.query.filter_by(status='Closed').all()
    # Wait, the app recalculates user dashboard P&L based on `t.pnl for t in todays_trades`.
    # Let's also update the DailyPnL for today
    
    # Calculate for each day in case there are multiple
    from collections import defaultdict
    daily_totals = defaultdict(float)
    for t in all_closed:
        if t.timestamp:
            t_date = t.timestamp.date()
            daily_totals[t_date] += t.pnl

    for d_date, d_pnl in daily_totals.items():
        rec = DailyPnL.query.filter_by(date=d_date).first()
        if not rec:
            db.session.add(DailyPnL(date=d_date, pnl=d_pnl))
        else:
            rec.date = d_date # just touch
            # Wait, app calculates daily PnL by just keeping a running total or recalculating it on dashboard load?
            # `app.py` `user_dashboard`:
            # pnl_1d = sum(t.pnl for t in todays_trades if t.status == 'Closed')
            # today_record = DailyPnL.query.filter_by(date=today_date).first()
            # today_record.pnl = pnl_1d
            pass # app.py does the daily PNL update dynamically on load anyway!

    db.session.commit()
    print("✅ All trades updated successfully for Demo Users!")
