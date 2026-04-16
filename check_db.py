import os
from app import app, db, User, AlgoTrade
with app.app_context():
    print(f"DEBUG: Using DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("--- USERS ---")
    for u in User.query.all():
        print(f"ID: {u.id}, Name: {u.username}, Phone: {u.phone}")
    print("\n--- RECENT TRADES ---")
    for t in AlgoTrade.query.order_by(AlgoTrade.timestamp.desc()).limit(20).all():
        print(f"Time: {t.timestamp}, Symbol: {t.symbol}, Type: {t.trade_type}, Price: {t.entry_price}, Exit: {t.exit_price}, Status: {t.status}, PnL: {t.pnl}")
