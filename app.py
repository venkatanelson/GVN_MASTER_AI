# -*- coding: utf-8 -*-
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
import threading
import sqlite3
import shared_data
import shoonya_live_feed 
import dhan_live_feed 
import broker_api
import pyotp 
from security_engine import SecurityShield 

# 🚀 GVN MASTER BUILD VERSION
BUILD_VERSION = "2.2.4 (Universal Bypass Ready)"
BUILD_DATE = "2026-04-28"

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

# --- DATABASE MODELS ---
class SystemState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    selected_index = db.Column(db.String(20), default="NIFTY")
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)

class TradeSignal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strike = db.Column(db.String(50))
    signal_type = db.Column(db.String(10))
    price = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminConfig(db.Model):
    __tablename__ = 'admin_system_config'
    id = db.Column(db.Integer, primary_key=True)
    admin_user = db.Column(db.String(50), default='admin')
    admin_pass = db.Column(db.String(50), default='Kalavathi@12')
    admin_phone = db.Column(db.String(15), default='9966123078')
    support_number_1 = db.Column(db.String(15), default='9381490610')
    support_number_2 = db.Column(db.String(15), default='9966123078')
    reset_otp = db.Column(db.String(10), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    attack_mode = db.Column(db.Boolean, default=False) 
    plan_basic_price = db.Column(db.Integer, default=2999)
    plan_premium_price = db.Column(db.Integer, default=5999)
    plan_ultimate_price = db.Column(db.Integer, default=9999)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    user_type = db.Column(db.String(10), default='REAL')
    demo_capital = db.Column(db.Integer, default=0) 
    selected_plan = db.Column(db.String(20)) 
    is_approved = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.DateTime)
    dhan_webhook_url = db.Column(db.String(300))
    encrypted_secret_key = db.Column(db.LargeBinary)
    algo_status = db.Column(db.String(10), default='OFF')
    admin_kill_switch = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False) 
    is_admin = db.Column(db.Boolean, default=False) 
    is_locked = db.Column(db.Boolean, default=True) 
    signals_unlocked_until = db.Column(db.DateTime, nullable=True) 
    personal_discount = db.Column(db.Integer, default=0)
    trade_lots = db.Column(db.Integer, default=1)
    full_auto_mode = db.Column(db.Boolean, default=False) 

class DailyPnL(db.Model):
    __tablename__ = 'daily_pnl_tracker'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    pnl = db.Column(db.Float, default=0.0)

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trades_v3'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=5, minutes=30))
    symbol = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    trade_type = db.Column(db.String(20)) 
    status = db.Column(db.String(20)) 
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float, nullable=True)
    target_price = db.Column(db.Float, nullable=True) 
    stop_loss = db.Column(db.Float, nullable=True)    
    pnl = db.Column(db.Float, default=0.0)
    ai_opinion = db.Column(db.String(500), nullable=True) 

class UserBrokerConfig(db.Model):
    __tablename__ = 'user_broker_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False)
    broker_name = db.Column(db.String(50), default="Dhan")
    webhook_url = db.Column(db.String(300))
    encrypted_secret_key = db.Column(db.LargeBinary)
    client_id = db.Column(db.String(100), nullable=True)
    encrypted_access_token = db.Column(db.LargeBinary, nullable=True)
    encrypted_client_secret = db.Column(db.LargeBinary, nullable=True) 
    encrypted_totp_key = db.Column(db.LargeBinary, nullable=True)     
    encrypted_password = db.Column(db.LargeBinary, nullable=True)     
    call_strike = db.Column(db.String(50), nullable=True)           
    put_strike = db.Column(db.String(50), nullable=True)            

class AIPaperTrade(db.Model):
    __tablename__ = 'ai_paper_trades'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=5, minutes=30))
    strike_selected = db.Column(db.String(100))
    delta_value = db.Column(db.Float)
    reason = db.Column(db.String(200))
    entry_price = db.Column(db.Float)
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="RUNNING")

class PaymentScreenshot(db.Model):
    __tablename__ = 'payment_screenshots'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    screenshot_path = db.Column(db.String(300), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=5, minutes=30))
    status = db.Column(db.String(20), default="PENDING") 
    utr_number = db.Column(db.String(100), nullable=True)
    plan_selected = db.Column(db.String(50), default="1-Day") 

# Encryption Key
static_32_byte_string = b'gvn_secure_key_for_encryption_26'
fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
cipher = Fernet(ENCRYPTION_KEY)

# TELEGRAM BOT CONFIG
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '1008887074')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '@indicator_Gvn') 

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN: return
    chat_ids = [cid.strip() for cid in str(TELEGRAM_CHAT_ID).split(',') if cid.strip()]
    if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID not in chat_ids:
        chat_ids.append(TELEGRAM_CHANNEL_ID)
    for cid in chat_ids:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try: requests.post(url, json={"chat_id": cid, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

security = SecurityShield(tg_sender=send_telegram_msg)

def get_admin_config():
    config = AdminConfig.query.first()
    if not config:
        config = AdminConfig()
        db.session.add(config)
        db.session.commit()
    return config

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        config = get_admin_config()
        if not auth or auth.username != config.admin_user or auth.password != config.admin_pass:
            return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# --- CORE ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user: return redirect(url_for('user_dashboard', user_id=user.id))
    return render_template('index.html', config=get_admin_config())

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    session['user_id'] = user_id
    user = User.query.get_or_404(user_id)
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    
    todays_trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).all()
    pnl_1d = sum((t.pnl or 0.0) for t in todays_trades if t.status == 'Closed')
    
    broker_config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    
    return render_template('user.html', 
                           user=user, 
                           broker_config=broker_config,
                           remaining_days=max(0, (user.expiry_date - now).days if user.expiry_date else 0),
                           pnl_1d=pnl_1d,
                           parsed_trades=todays_trades,
                           config=get_admin_config(),
                           build_version=BUILD_VERSION)

@app.route('/api/gvn-scanner')
def gvn_scanner():
    target_idx = getattr(shared_data, 'selected_index', 'NIFTY')
    n_price = shared_data.live_option_chain_summary.get(target_idx, {}).get('spot', 0)
    
    user_id = session.get('user_id')
    user_strikes = {"CALL": "N/A", "PUT": "N/A"}
    if user_id:
        conf = UserBrokerConfig.query.filter_by(user_id=user_id).first()
        if conf:
            user_strikes["CALL"] = conf.call_strike or "N/A"
            user_strikes["PUT"] = conf.put_strike or "N/A"

    return jsonify({
        "status": "success",
        "data": shared_data.gvn_scanner_data,
        "summary": shared_data.live_option_chain_summary,
        "nifty_spot": n_price,
        "user_strikes": user_strikes,
        "selected_index": target_idx
    })

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    try:
        data = request.json
        user_msg = data.get('message', '')
        idx = data.get('index', 'NIFTY')
        
        from dotenv import dotenv_values
        api_key = (os.environ.get('GROQ_API_KEY') or '').strip()
        if not api_key: return jsonify({"reply": "⚠️ GROQ_API_KEY not set!"})
        
        summary = shared_data.live_option_chain_summary.get(idx, {})
        n_spot = summary.get('spot', 0)
        
        context = f"LIVE MARKET - {idx} Spot: {n_spot}. Analyze Option Chain for Zero-to-Hero setups."
        system_prompt = "You are GVN Master AI expert. Analyze the market. CRITICAL: Provide response in TELUGU language."
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\nUser: {user_msg}"}
            ],
            "temperature": 0.4
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            return jsonify({"reply": response.json()['choices'][0]['message']['content']})
        return jsonify({"reply": f"AI Error: HTTP {response.status_code}"})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

def send_premium_telegram_alert(signal_data):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id: return
    msg = (
        f"🚀 <b>GVN MASTER ALGO: NEW SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>STRIKE:</b> {signal_data['strike']}\n"
        f"⚡ <b>SIGNAL:</b> {signal_data['type']} @ ₹{signal_data['price']}\n"
        f"🎯 <b>TARGET:</b> ₹{signal_data['target']}\n"
        f"🛑 <b>STOP LOSS:</b> ₹{signal_data['sl']}\n"
        f"🛰️ <b>ZONE:</b> {signal_data['zone']}\n"
    )
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except: pass

def gvn_signal_engine():
    print("🚀 [GVN SIGNAL ENGINE] Monitoring Alpha Grid...")
    while True:
        try:
            target_idx = getattr(shared_data, 'selected_index', 'NIFTY')
            scanner_data = shared_data.gvn_scanner_data.get(target_idx, [])
            for item in scanner_data:
                if item.get('levels') and item['ltp'] > item['levels']['i5']:
                    # Anti-Spam (15 min)
                    last_sent = shared_data.last_signal_time.get(item['strike'], 0)
                    if time.time() - last_sent > 900: 
                        alert = {
                            "strike": item['strike'], "type": "BUY", "price": item['ltp'],
                            "target": round(item['ltp'] * 1.2, 2), "sl": round(item['ltp'] * 0.8, 2),
                            "zone": item['zone'], "score": item.get('score', 80)
                        }
                        send_premium_telegram_alert(alert)
                        shared_data.last_signal_time[item['strike']] = time.time()
                        shared_data.auto_trade_signals.insert(0, alert)
            time.sleep(3)
        except Exception as e:
            print(f"❌ [SIGNAL ENGINE ERROR] {e}")
            time.sleep(10)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    threading.Thread(target=gvn_signal_engine, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)