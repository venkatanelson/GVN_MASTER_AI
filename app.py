import os
from dotenv import load_dotenv
load_dotenv()
import base64
import requests
import time
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import shared_data

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_flask_key_2026')
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    algo_status = db.Column(db.String(10), default='OFF')
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=True)

class UserBrokerConfig(db.Model):
    __tablename__ = 'user_broker_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    broker_name = db.Column(db.String(50), default="Shoonya")
    client_id = db.Column(db.String(100))
    encrypted_password = db.Column(db.LargeBinary)
    api_key = db.Column(db.String(200))
    api_secret = db.Column(db.String(200))
    totp_key = db.Column(db.String(100))

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trades_v3'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(100))
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Closed')

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('user_dashboard', user_id=session['user_id']))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login-auto')
def login_auto():
    if request.method == 'POST':
        identifier = request.form.get('login_phone', '').strip().lower()
        user = User.query.filter((User.phone == identifier) | (User.email == identifier)).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard', user_id=user.id))
    session['user_id'] = 1
    return redirect(url_for('user_dashboard', user_id=1))

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    user = db.session.get(User, user_id)
    if not user: return redirect(url_for('index'))
    trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).limit(20).all()
    config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    
    password = ""
    if config and config.encrypted_password:
        try: password = cipher.decrypt(config.encrypted_password).decode()
        except: pass

    return render_template('user.html', user=user, todays_trades=trades, config=config, password=password)

@app.route('/admin')
@app.route('/admin-control')
def admin_dashboard():
    v = db.session.get(User, 1)
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

@app.route('/toggle-algo/<int:user_id>')
def toggle_algo(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.algo_status = "ON" if user.algo_status == "OFF" else "OFF"
        db.session.commit()
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    uid = session.get('user_id', 1)
    data = request.form
    config = UserBrokerConfig.query.filter_by(user_id=uid).first()
    if not config:
        config = UserBrokerConfig(user_id=uid); db.session.add(config)
    config.broker_name = data.get('broker_name', 'Shoonya')
    config.client_id = data.get('client_id')
    if data.get('password'):
        config.encrypted_password = cipher.encrypt(data.get('password').encode())
    config.api_key = data.get('api_key')
    config.api_secret = data.get('api_secret')
    config.totp_key = data.get('totp_key')
    db.session.commit()
    flash("API Settings Saved!")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- INITIALIZATION ---
def init_gvn():
    with app.app_context():
        db.create_all()
        if not db.session.get(User, 1):
            v = User(id=1, username="Venkat", phone="9966123078", email="nelsonp143@gmail.com", is_admin=True, algo_status="OFF")
            db.session.add(v); db.session.commit()
        
        try:
            import shoonya_live_feed
            shoonya_live_feed.start_live_feed_worker()
        except Exception as e:
            print(f"⚠️ Feed Worker Start Failed: {e}")

init_gvn()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)