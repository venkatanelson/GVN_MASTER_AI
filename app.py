import os
import datetime
from datetime import datetime, timedelta
import time
import threading
import random
import requests
import json
import base64
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
import shared_data
import gvn_levels_engine

app = Flask(__name__)
app.secret_key = 'gvn_master_venkat_stable_key'

# Database Configuration
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_master_algo.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), default="Venkat")
    email = db.Column(db.String(120), default="nelsonp143@gmail.com")
    algo_status = db.Column(db.String(10), default='OFF')
    trade_lots = db.Column(db.Integer, default=1)

class AlgoTrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(50))
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Closed')

class DailyPnL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    pnl = db.Column(db.Float, default=0.0)

class MarketData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True)
    price = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class UserBrokerConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    broker_name = db.Column(db.String(50))
    client_id = db.Column(db.String(100))
    encrypted_password = db.Column(db.LargeBinary) # 🌟 FIXED: LargeBinary
    encrypted_access_token = db.Column(db.LargeBinary) # 🌟 FIXED: LargeBinary

# Security
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
cipher = Fernet(ENCRYPTION_KEY)

# --- MASTER INITIALIZATION ---
with app.app_context():
    db.create_all()
    # 🌟 RESTORE OR CREATE USER 'Venkat'
    venkat = User.query.filter_by(username='Venkat').first()
    if not venkat:
        venkat = User(username='Venkat', email='nelsonp143@gmail.com')
        db.session.add(venkat)
        db.session.commit()
    
    # Clean up old users (like Muryhy/Manikanta) to avoid confusion
    old_users = User.query.filter(User.username != 'Venkat').all()
    for u in old_users: 
        # Move their trades to Venkat if any
        AlgoTrade.query.filter_by(user_id=u.id).update({"user_id": venkat.id})
        DailyPnL.query.filter_by(user_id=u.id).update({"user_id": venkat.id})
        db.session.delete(u)
    db.session.commit()

    # 🌟 P&L RECOVERY
    try:
        conn = db.engine.connect()
        legacy_tables = ["algo_trades_v3", "user_dashboard_trades", "trades_old"]
        for table in legacy_tables:
            try:
                # One-time sync: check if table has rows
                res = conn.execute(db.text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                if res and res[0] > 0:
                    conn.execute(db.text(f"INSERT INTO algo_trade (user_id, symbol, pnl, status, timestamp) SELECT {venkat.id}, 'Legacy RECOVERY', pnl, 'Closed', datetime('now') FROM {table} WHERE pnl IS NOT NULL"))
                    conn.execute(db.text(f"INSERT INTO daily_pnl (user_id, pnl, date) SELECT {venkat.id}, SUM(pnl), date('now') FROM {table} WHERE pnl IS NOT NULL GROUP BY date('now')"))
                    conn.commit()
                    print(f"✅ [STABLE] Recovered {table} for Venkat")
            except: pass
        conn.close()
    except: pass

# --- ROUTES ---
@app.route('/')
def index():
    user = User.query.filter_by(username='Venkat').first()
    if user: return redirect(url_for('user_dashboard', user_id=user.id))
    return render_template('index.html')

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    session['user_id'] = user_id
    user = User.query.get_or_404(user_id)
    
    # Summary Data
    trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).limit(20).all()
    pnl_1d = sum(t.pnl for t in trades if t.timestamp.date() == datetime.utcnow().date())
    
    daily_history = DailyPnL.query.filter_by(user_id=user_id).order_by(DailyPnL.date.desc()).limit(30).all()
    total_30d = sum(d.pnl for d in daily_history)
    
    # Spot Price
    md = MarketData.query.filter_by(symbol='NIFTY').first()
    spot_price = md.price if md else 0.0
    
    return render_template('user.html', user=user, todays_trades=trades, pnl_1d=pnl_1d, pnl_total_30d=total_30d, spot_price=spot_price)

@app.route('/api/broker-status')
def broker_status():
    md = MarketData.query.filter_by(symbol='NIFTY').first()
    spot = md.price if md else 0.0
    return jsonify({
        "connected": True if spot > 0 else False,
        "broker_name": "Universal",
        "spot": spot,
        "last_checked": datetime.now().strftime("%H:%M:%S")
    })

@app.route('/api/gvn-scanner')
def gvn_scanner():
    symbol = request.args.get('index', 'NIFTY')
    md = MarketData.query.filter_by(symbol=symbol).first()
    spot = md.price if md else 0.0
    return jsonify({
        "spot": spot,
        "data": shared_data.gvn_scanner_data.get(symbol, []),
        "pulse": shared_data.market_pulse
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
