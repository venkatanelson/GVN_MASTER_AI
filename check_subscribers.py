from app import app, db, AlgoTrade

with app.app_context():
    trades = AlgoTrade.query.all()
    print("--- LIVE DATABASE (NEON DB) TRADES TODAY ---")
    print("Total Trades Recorded:", len(trades))
    for t in trades[:5]:
        print(t.timestamp, t.symbol, t.trade_type, t.status)
