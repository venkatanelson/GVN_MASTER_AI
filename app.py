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
import shared_data
import shoonya_live_feed 
import dhan_live_feed 
import broker_api

# 🚀 GVN MASTER BUILD VERSION
BUILD_VERSION = "2.2.5 (Recovery & Master Sync)"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_flask_key_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31) 

db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---
class AdminConfig(db.Model):
    __tablename__ = 'admin_system_config'
    id = db.Column(db.Integer, primary_key=True)
    admin_user = db.Column(db.String(50), default='admin')
    admin_pass = db.Column(db.String(50), default='Kalavathi@12')
    admin_phone = db.Column(db.String(15), default='9966123078')
    support_number_1 = db.Column(db.String(15), default='9381490610')
    support_number_2 = db.Column(db.String(15), default='9966123078')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    user_type = db.Column(db.String(10), default='REAL')
    demo_capital = db.Column(db.Integer, default=0)
    selected_plan = db.Column(db.String(50))
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
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True)
    pnl = db.Column(db.Float, default=0.0)

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trade'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    trade_type = db.Column(db.String(20))
    status = db.Column(db.String(20))
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, default=0.0)
    target_price = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)

class UserBrokerConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    broker_name = db.Column(db.String(50), default="Dhan")
    webhook_url = db.Column(db.String(300))
    encrypted_secret_key = db.Column(db.LargeBinary)
    client_id = db.Column(db.String(100))
    encrypted_access_token = db.Column(db.LargeBinary)
    encrypted_client_secret = db.Column(db.LargeBinary)
    encrypted_totp_key = db.Column(db.LargeBinary)
    encrypted_password = db.Column(db.LargeBinary)
    call_strike = db.Column(db.String(50))
    put_strike = db.Column(db.String(50))

# Security
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))
cipher = Fernet(ENCRYPTION_KEY)

def get_admin_config():
    config = AdminConfig.query.first()
    if not config: config = AdminConfig(); db.session.add(config); db.session.commit()
    return config

# --- MIGRATIONS & RECOVERY ---
with app.app_context():
    db.create_all()
    try:
        conn = db.engine.connect()
        # 🛡️ RECOVERY: Merge old data if tables exist
        tables_to_sync = [("algo_trades_v3", "algo_trade"), ("daily_pnl_old", "daily_pnl")]
        for old, new in tables_to_sync:
            try:
                conn.execute(db.text(f"INSERT INTO {new} SELECT * FROM {old} WHERE id NOT IN (SELECT id FROM {new})"))
                conn.commit()
                print(f"✅ [RECOVERY] Synced data from {old} to {new}")
            except: pass
            
        # Add columns for robustness
        user_cols = [("email", "VARCHAR(100)"), ("demo_capital", "INTEGER DEFAULT 0"), ("selected_plan", "VARCHAR(50)"), ("is_approved", "BOOLEAN DEFAULT 0"), ("dhan_webhook_url", "VARCHAR(300)"), ("encrypted_secret_key", "BYTEA" if "postgres" in db_url else "BLOB"), ("algo_status", "VARCHAR(10) DEFAULT 'OFF'"), ("admin_kill_switch", "BOOLEAN DEFAULT FALSE"), ("is_blocked", "BOOLEAN DEFAULT FALSE"), ("is_admin", "BOOLEAN DEFAULT FALSE"), ("is_locked", "BOOLEAN DEFAULT TRUE"), ("signals_unlocked_until", "TIMESTAMP"), ("trade_lots", "INTEGER DEFAULT 1"), ("full_auto_mode", "BOOLEAN DEFAULT FALSE")]
        for col, ctype in user_cols:
            try: conn.execute(db.text(f"ALTER TABLE \"user\" ADD COLUMN {col} {ctype}")); conn.commit()
            except: pass
            
        trade_cols = [("exit_price", "FLOAT"), ("target_price", "FLOAT"), ("stop_loss", "FLOAT")]
        for col, ctype in trade_cols:
            try: conn.execute(db.text(f"ALTER TABLE algo_trade ADD COLUMN {col} {ctype}")); conn.commit()
            except: pass
        conn.close()
        print("✅ [DATABASE] Master Sync Completed.")
    except Exception as e: print(f"⚠️ [MIGRATION WARNING] {e}")

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('user_dashboard', user_id=session['user_id']))
    return render_template('index.html', config=get_admin_config())

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    session.permanent = True; session['user_id'] = user_id
    user = User.query.get_or_404(user_id)
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    todays_trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).all()
    pnl_1d = sum((t.pnl or 0.0) for t in todays_trades if t.status == 'Closed')
    all_daily = DailyPnL.query.order_by(DailyPnL.date.desc()).limit(30).all()
    daily_history = [{'date': dp.date.strftime("%d %b"), 'pnl': (dp.pnl or 0.0)} for dp in all_daily]
    pnl_total_30d = sum(dp['pnl'] for dp in daily_history)
    broker_config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    decrypted_keys = {"tv_secret": "", "access_token": "", "client_secret": "", "totp_key": "", "broker_password": ""}
    if broker_config:
        try:
            if broker_config.encrypted_secret_key: decrypted_keys["tv_secret"] = cipher.decrypt(broker_config.encrypted_secret_key).decode()
            if broker_config.encrypted_access_token: decrypted_keys["access_token"] = cipher.decrypt(broker_config.encrypted_access_token).decode()
            if broker_config.encrypted_client_secret: decrypted_keys["client_secret"] = cipher.decrypt(broker_config.encrypted_client_secret).decode()
            if broker_config.encrypted_totp_key: decrypted_keys["totp_key"] = cipher.decrypt(broker_config.encrypted_totp_key).decode()
            if broker_config.encrypted_password: decrypted_keys["broker_password"] = cipher.decrypt(broker_config.encrypted_password).decode()
        except: pass
    return render_template('user.html', user=user, broker_config=broker_config, decrypted_keys=decrypted_keys, remaining_days=max(0, (user.expiry_date - now).days if user.expiry_date else 0), pnl_1d=pnl_1d, pnl_total_30d=pnl_total_30d, daily_history=daily_history, discount_percent=user.personal_discount + 10, parsed_trades=todays_trades, config=get_admin_config(), build_version=BUILD_VERSION, cache_id=int(time.time()))

@app.route('/toggle-algo/<int:user_id>')
def toggle_algo(user_id):
    user = User.query.get_or_404(user_id); user.algo_status = 'ON' if user.algo_status == 'OFF' else 'OFF'
    db.session.commit(); flash(f"Algo Master Switch: {user.algo_status}")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/toggle-auto-mode/<int:user_id>')
def toggle_auto_mode(user_id):
    user = User.query.get_or_404(user_id); user.full_auto_mode = not user.full_auto_mode
    db.session.commit(); flash(f"GVN Pilot: {'ACTIVE' if user.full_auto_mode else 'DISABLED'}")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    user_id = request.form.get('user_id')
    conf = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    if not conf: conf = UserBrokerConfig(user_id=user_id); db.session.add(conf)
    conf.broker_name = request.form.get('broker_name'); conf.client_id = request.form.get('client_id'); conf.webhook_url = request.form.get('webhook_url')
    conf.call_strike = request.form.get('call_strike'); conf.put_strike = request.form.get('put_strike')
    sk = request.form.get('secret_key')
    if sk and sk != '********': conf.encrypted_secret_key = cipher.encrypt(sk.encode())
    at = request.form.get('access_token')
    if at and at != '********': conf.encrypted_access_token = cipher.encrypt(at.encode())
    db.session.commit(); flash("API Settings Saved!")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/api/gvn-scanner')
def gvn_scanner():
    target_idx = getattr(shared_data, 'selected_index', 'NIFTY')
    n_price = shared_data.live_option_chain_summary.get(target_idx, {}).get('spot', 0)
    user_id = session.get('user_id'); user_strikes = {"CALL": "N/A", "PUT": "N/A"}
    if user_id:
        conf = UserBrokerConfig.query.filter_by(user_id=user_id).first()
        if conf: user_strikes["CALL"] = conf.call_strike or "N/A"; user_strikes["PUT"] = conf.put_strike or "N/A"
    return jsonify({"status": "success", "data": shared_data.gvn_scanner_data, "summary": shared_data.live_option_chain_summary, "nifty_spot": n_price, "user_strikes": user_strikes, "selected_index": target_idx})

@app.route('/api/broker-status')
def broker_status():
    status = shared_data.broker_connection_status.copy()
    status["nifty_spot"] = shared_data.live_option_chain_summary.get(getattr(shared_data, 'selected_index', 'NIFTY'), {}).get("spot", 0)
    return jsonify(status)

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    try:
        data = request.json; api_key = os.environ.get('GROQ_API_KEY', '').strip()
        if not api_key: return jsonify({"reply": "⚠️ AI Offline"})
        idx = data.get('index', 'NIFTY'); spot = shared_data.live_option_chain_summary.get(idx, {}).get('spot', 0)
        payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": "You are GVN Master AI. Analyze and Reply in TELUGU language."}, {"role": "user", "content": f"Spot: {spot}. Index: {idx}. Msg: {data.get('message')}"}]}
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=15)
        return jsonify({"reply": resp.json()['choices'][0]['message']['content'] if resp.status_code == 200 else "AI Error"})
    except Exception as e: return jsonify({"reply": f"AI Error: {e}"})

# --- BACKGROUND ENGINE ---
def gvn_signal_engine():
    print("🚀 [GVN SIGNAL ENGINE] Monitoring Alpha Grid...")
    while True:
        try:
            idx = getattr(shared_data, 'selected_index', 'NIFTY')
            scanner_data = shared_data.gvn_scanner_data.get(idx, [])
            spot = shared_data.live_option_chain_summary.get(idx, {}).get('spot', 0)
            for item in scanner_data:
                if item.get('levels') and item['ltp'] > item['levels']['i5']:
                    if time.time() - shared_data.last_signal_time.get(item['strike'], 0) > 900:
                        msg = f"🚀 <b>GVN MASTER ALGO: NEW SIGNAL</b>\n━━━━━━━━━━━━━━━━━━━━\n📦 <b>STRIKE:</b> <code>{item['strike']}</code>\n⚡ <b>SIGNAL:</b> <b>BUY</b> @ ₹{item['ltp']}\n📊 <b>PULSE SCORE:</b> {item.get('score', 75)}%\n🛰️ <b>ZONE:</b> ALPHA ZONE\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>AI Validation:</b> CONFIRMED ✅"
                        token, cid = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
                        if token and cid: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": cid, "text": msg, "parse_mode": "HTML"}, timeout=5)
                        shared_data.last_signal_time[item['strike']] = time.time()
            time.sleep(2)
        except Exception: time.sleep(5)

if __name__ == '__main__':
    if not getattr(app, '_workers_started', False):
        threading.Thread(target=gvn_signal_engine, daemon=True).start()
        app._workers_started = True
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False)
