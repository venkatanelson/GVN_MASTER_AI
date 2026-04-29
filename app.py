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
from sqlalchemy import text
from cryptography.fernet import Fernet
import shared_data
import gvn_levels_engine

app = Flask(__name__)
app.secret_key = 'gvn_master_venkat_final_stable'

# Database Configuration
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_master_algo.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    algo_status = db.Column(db.String(10), default='OFF')

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trade'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(50))
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Closed')

class DailyPnL(db.Model):
    __tablename__ = 'daily_pnl'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    pnl = db.Column(db.Float, default=0.0)

class MarketData(db.Model):
    __tablename__ = 'market_data'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True)
    price = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class UserBrokerConfig(db.Model):
    __tablename__ = 'user_broker_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    broker_name = db.Column(db.String(50))
    client_id = db.Column(db.String(100))
    encrypted_password = db.Column(db.LargeBinary)
    encrypted_access_token = db.Column(db.LargeBinary)

# Security
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
cipher = Fernet(ENCRYPTION_KEY)

# --- MIGRATIONS & SETUP ---
def run_setup():
    with app.app_context():
        db.create_all()
        conn = db.engine.connect()
        
        # 🌟 Ensure User 'Venkat' exists
        v = User.query.filter_by(username='Venkat').first()
        if not v:
            v = User(username='Venkat', email='nelsonp143@gmail.com')
            db.session.add(v)
            db.session.commit()
            print("✅ User 'Venkat' created.")

        # 🌟 P&L Recovery
        legacy_tables = ["algo_trades_v3", "user_dashboard_trades", "trades_old"]
        for table in legacy_tables:
            try:
                # Check if data exists in legacy
                res = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                if res and res[0] > 0:
                    # Sync to Venkat's account
                    conn.execute(text(f"INSERT INTO algo_trade (user_id, symbol, pnl, status, timestamp) SELECT {v.id}, 'RECOVERY', pnl, 'Closed', datetime('now') FROM {table} WHERE pnl IS NOT NULL"))
                    conn.execute(text(f"INSERT INTO daily_pnl (user_id, pnl, date) SELECT {v.id}, SUM(pnl), date('now') FROM {table} WHERE pnl IS NOT NULL GROUP BY date('now')"))
                    conn.commit()
                    print(f"✅ Data recovered from {table}")
            except: pass
        conn.close()

run_setup()

# --- ROUTES ---
@app.route('/')
def index():
    v = User.query.filter_by(username='Venkat').first()
    if v: return redirect(url_for('user_dashboard', user_id=v.id))
    return "User not found. Check database setup."

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).all()
    pnl_1d = sum(t.pnl for t in trades if t.timestamp.date() == datetime.utcnow().date())
    
    daily = DailyPnL.query.filter_by(user_id=user_id).order_by(DailyPnL.date.desc()).limit(30).all()
    pnl_30d = sum(d.pnl for d in daily)
    
    md = MarketData.query.filter_by(symbol='NIFTY').first()
    spot = md.price if md else 0.0
    
    return render_template('user.html', user=user, todays_trades=trades, pnl_1d=pnl_1d, pnl_total_30d=pnl_30d, spot_price=spot)

@app.route('/api/broker-status')
def broker_status():
    md = MarketData.query.filter_by(symbol='NIFTY').first()
    spot = md.price if md else 0.0
    return jsonify({"connected": True if spot > 0 else False, "broker_name": "Shoonya", "spot": spot})

@app.route('/api/gvn-scanner')
def gvn_scanner():
    symbol = request.args.get('index', 'NIFTY')
    md = MarketData.query.filter_by(symbol=symbol).first()
    return jsonify({"spot": md.price if md else 0.0, "data": shared_data.gvn_scanner_data.get(symbol, []), "pulse": shared_data.market_pulse})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
