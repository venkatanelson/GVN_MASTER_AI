import os
from dotenv import load_dotenv
load_dotenv()
import base64
import requests
import time
import concurrent.futures
from functools import wraps
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, Response, session
import random
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import sqlite3
import shared_data
import shoonya_live_feed 
import broker_api
import pyotp 
from dhanhq import dhanhq
from security_engine import SecurityShield 

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_flask_key_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31) 

db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 280}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

static_32_byte_string = b'gvn_secure_key_for_encryption_26'
fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
cipher = Fernet(ENCRYPTION_KEY)

# ---------------------------------------------------------
# TELEGRAM BOT CONFIG
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '1008887074')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '@indicator_Gvn') 

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN: return
    chat_ids = [cid.strip() for cid in str(TELEGRAM_CHAT_ID).split(',') if cid.strip()]
    if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID not in chat_ids: chat_ids.append(TELEGRAM_CHANNEL_ID)
    for cid in chat_ids:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": cid, "text": message, "parse_mode": "HTML"}
        try: requests.post(url, json=payload, timeout=5)
        except: pass

security = SecurityShield(tg_sender=send_telegram_msg)

# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
class AdminConfig(db.Model):
    __tablename__ = 'admin_system_config'
    id = db.Column(db.Integer, primary_key=True)
    admin_user = db.Column(db.String(50), default='admin')
    admin_pass = db.Column(db.String(50), default='Kalavathi@12')
    admin_phone = db.Column(db.String(15), default='9966123078')
    attack_mode = db.Column(db.Boolean, default=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    user_type = db.Column(db.String(10), default='REAL')
    is_approved = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.DateTime)
    algo_status = db.Column(db.String(10), default='OFF')
    is_blocked = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trades_v3'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    trade_type = db.Column(db.String(20))
    status = db.Column(db.String(20))
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float)
    pnl = db.Column(db.Float, default=0.0)

class UserBrokerConfig(db.Model):
    __tablename__ = 'user_broker_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    broker_name = db.Column(db.String(50), default="Shoonya")
    client_id = db.Column(db.String(100))
    encrypted_password = db.Column(db.LargeBinary)
    encrypted_secret_key = db.Column(db.LargeBinary)
    webhook_url = db.Column(db.String(300))

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard', user_id=session['user_id']))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login-auto')
def login_auto():
    if request.method == 'POST':
        identifier = request.form.get('login_phone', '').strip().lower()
        user = User.query.filter((User.phone == identifier) | (User.email == identifier)).first()
        if user:
            if user.is_blocked: return "Blocked", 403
            session.permanent = True
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard', user_id=user.id))
    
    # Auto-login for Venkat
    session['user_id'] = 1
    session['is_admin'] = True
    return redirect(url_for('user_dashboard', user_id=1))

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    session['user_id'] = user_id
    user = User.query.get_or_404(user_id)
    trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).limit(50).all()
    pnl_1d = sum(t.pnl for t in trades if t.timestamp.date() == datetime.utcnow().date())
    
    config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    password = ""
    if config and config.encrypted_password:
        try: password = cipher.decrypt(config.encrypted_password).decode()
        except: pass

    return render_template('user.html', user=user, todays_trades=trades, pnl_1d=pnl_1d, config=config, password=password)

@app.route('/admin')
def admin_dashboard():
    session['user_id'] = 1
    session['is_admin'] = True
    v = User.query.get(1)
    config = UserBrokerConfig.query.filter_by(user_id=1).first()
    return render_template('admin.html', user=v, config=config)

@app.route('/api/gvn-scanner')
def gvn_scanner():
    return jsonify({
        "status": "success",
        "alpha_grid": shared_data.gvn_alpha_grid,
        "market_pulse": shared_data.market_pulse,
        "nifty_spot": shared_data.market_data.get("NIFTY", 0)
    })

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    uid = session.get('user_id')
    if not uid: return jsonify({"status": "error"}), 401
    data = request.form
    config = UserBrokerConfig.query.filter_by(user_id=uid).first()
    if not config:
        config = UserBrokerConfig(user_id=uid); db.session.add(config)
    config.broker_name = data.get('broker_name', 'Shoonya')
    config.client_id = data.get('client_id')
    if data.get('password'):
        config.encrypted_password = cipher.encrypt(data.get('password').encode())
    db.session.commit()
    flash("API Settings Saved!")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.get(1):
            db.session.add(User(id=1, username="Venkat", phone="9966123078", email="nelsonp143@gmail.com", is_admin=True, is_approved=True))
            db.session.commit()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
