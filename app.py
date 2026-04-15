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

app = Flask(__name__)

# Basic app config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_flask_key_2026')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31) # 🌟 NEW: Auto-login lasts 1 month

# 🌟 NEW: Neon PostgreSQL Database URL
# If DATABASE_URL is in the environment (e.g., Render/Neon), use Postgres. Otherwise, use local SQLite.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
# Quick fix for Render & SQLAlchemy (replace postgres:// with postgresql://)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 280}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Encryption Key
static_32_byte_string = b'gvn_secure_key_for_encryption_26'
fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
cipher = Fernet(ENCRYPTION_KEY)

# ---------------------------------------------------------
# TELEGRAM BOT CONFIG
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '1008887074')

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM ERROR: Bot Token or Chat ID not found!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"TELEGRAM SEND ERROR: {e}")

# ---------------------------------------------------------
# DYNAMIC ADMIN CONFIG & AUTHENTICATION
# ---------------------------------------------------------
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

def get_admin_config():
    config = AdminConfig.query.first()
    if not config:
        config = AdminConfig()
        db.session.add(config)
        db.session.commit()
    return config

def check_auth(username, password):
    config = AdminConfig.query.first()
    if not config: return username == 'admin' and password == 'Kalavathi@12'
    return username == config.admin_user and password == config.admin_pass

def authenticate():
    return Response(
        '''
        <html>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h2>🚨 Admin Access Required</h2>
            <p>Authentication failed or was cancelled.</p>
            <p>If you forgot your password, <br><br>
            <a href="/admin-reset" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">Recover via Phone OTP</a></p>
        </body>
        </html>
        ''', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------
# DATABASE MODELS
# ---------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    
    # 🌟 NEW: Split User Type (REAL vs DEMO)
    user_type = db.Column(db.String(10), default='REAL')
    demo_capital = db.Column(db.Integer, default=0) # Between 50k and 1L typically
    
    # Subscription Details
    selected_plan = db.Column(db.String(20)) # Basic, Premium, Ultimate
    is_approved = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.DateTime)
    
    # API & Algo Control (Unused by Demo)
    dhan_webhook_url = db.Column(db.String(300))
    encrypted_secret_key = db.Column(db.LargeBinary)
    algo_status = db.Column(db.String(10), default='OFF')
    admin_kill_switch = db.Column(db.Boolean, default=False)
    
    # Discounts
    personal_discount = db.Column(db.Integer, default=0)

class DailyPnL(db.Model):
    __tablename__ = 'daily_pnl_tracker'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    pnl = db.Column(db.Float, default=0.0)

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trades_v3'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # 🌟 NEW: Link to User
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=5, minutes=30))
    symbol = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    trade_type = db.Column(db.String(20)) # BUY, SELL
    status = db.Column(db.String(20)) # Running, Closed
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, default=0.0)

class UserBrokerConfig(db.Model):
    __tablename__ = 'user_broker_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False)
    broker_name = db.Column(db.String(50), default="Dhan")
    webhook_url = db.Column(db.String(300))
    encrypted_secret_key = db.Column(db.LargeBinary)

# ---------------------------------------------------------
# REGISTRATION & ROUTES
# ---------------------------------------------------------

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('user_dashboard', user_id=user.id))
    return render_template('index.html', config=get_admin_config())

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/demo-register', methods=['POST'])
def demo_register():
    # 🌟 Auto-login check
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('user_dashboard', user_id=user.id))

    username = request.form.get('username', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip().lower()
    try:
        capital = int(request.form.get('demo_capital', 50000))
    except ValueError:
        capital = 50000
    
    # Robust existing user check
    existing = User.query.filter(
        db.or_(db.func.lower(User.email) == email, User.phone == phone)
    ).first()
    
    if existing:
        session.permanent = True
        session['user_id'] = existing.id
        return redirect(url_for('user_dashboard', user_id=existing.id))
        
    # Protect capital limits (50k to 1 Lakh)
    if capital < 50000: capital = 50000
    if capital > 100000: capital = 100000
    
    new_user = User(
        username=username,
        phone=phone,
        email=email,
        user_type='DEMO',
        demo_capital=capital,
        selected_plan='Demo Trial',
        is_approved=True,
        expiry_date=datetime.utcnow() + timedelta(hours=5, minutes=30, days=30),
        algo_status='ON'
    )
    db.session.add(new_user)
    try:
        db.session.commit()
        session.permanent = True
        session['user_id'] = new_user.id
        return redirect(url_for('user_dashboard', user_id=new_user.id))
    except Exception as e:
        db.session.rollback()
        # If database raised unique constraint error despite our prior check
        fallback = User.query.filter((User.email.ilike(email)) | (User.phone == phone)).first()
        if fallback:
            session.permanent = True
            session['user_id'] = fallback.id
            return redirect(url_for('user_dashboard', user_id=fallback.id))
        flash("Registration Failed: Email or Phone might already exist!")
        return redirect(url_for('index'))


@app.route('/login', methods=['POST'])
def simple_login():
    identifier = request.form.get('login_phone', '').strip().lower()
    
    # 🔍 Search by Phone OR Email (more forgiving)
    user = User.query.filter((User.phone == identifier) | (User.email == identifier)).first()
    
    if user:
        session.permanent = True
        session['user_id'] = user.id
        return redirect(url_for('user_dashboard', user_id=user.id))
    return f"""
    <div style='text-align:center; font-family:sans-serif; margin-top:100px; padding:20px; border:1px solid #ddd; background:#fff;'>
        <h3 style='color:red;'>Phone/Email not found ({identifier})!</h3>
        <p>Please register as a New User first OR check if your database on Render is connected correctly.</p>
        <a href='/' style='background:#1a73e8; color:#fff; padding:10px 20px; text-decoration:none; border-radius:5px;'>Go back to Registration</a>
    </div>"""

@app.route('/plans')
def subscription_plans():
    return render_template('plans.html')

def square_off_user_trades(user, reason, manual_price=None):
    active_trades = AlgoTrade.query.filter_by(user_id=user.id, status='Running').all()
    if not active_trades: return
    for t in active_trades:
        t.status = 'Closed'
        t.exit_price = float(manual_price) if manual_price else t.entry_price
        t.pnl = (t.exit_price - t.entry_price) * t.quantity
        
        if user.user_type == 'REAL' and user.is_approved:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
                webhook_url = broker_conf.webhook_url if broker_conf else user.dhan_webhook_url
                enc_secret = broker_conf.encrypted_secret_key if broker_conf else user.encrypted_secret_key
                broker_name = broker_conf.broker_name if broker_conf else "Dhan"
                if enc_secret and webhook_url:
                    secret_key = cipher.decrypt(enc_secret).decode()
                    if broker_name.lower() == 'dhan':
                        payload = {"secret": secret_key, "alertType": "multi_leg_order", "order_legs": [{"transactionType": "S", "orderType": "MKT", "quantity": str(t.quantity), "exchange": "NFO" if ("NIFTY" in t.symbol.upper() or "BANK" in t.symbol.upper() or "SENSEX" in t.symbol.upper()) else "NSE", "symbol": t.symbol, "instrument": "OPT" if ("NIFTY" in t.symbol.upper() or "BANK" in t.symbol.upper() or "SENSEX" in t.symbol.upper()) else "EQ", "productType": "M"}]}
                    else:
                        payload = {"secret": secret_key, "symbol": t.symbol, "quantity": t.quantity, "transactionType": "SELL", "orderType": "MARKET", "productType": "MARGIN", "message": reason}
                    threading.Thread(target=requests.post, args=(webhook_url,), kwargs={'json': payload, 'timeout': 5}).start()
            except Exception as e:
                print(f"Square-off error for {user.username}: {e}", flush=True)

@app.route('/toggle-algo/<int:user_id>')
def toggle_algo(user_id):
    user = User.query.get_or_404(user_id)
    if user.algo_status == 'ON':
        user.algo_status = 'OFF'
        manual_price = request.args.get('exit_price')
        square_off_user_trades(user, "User Paused Dashboard", manual_price)
        db.session.commit()
        flash("Algo Stopped and Positions Squared Off Successfully.")
    else:
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        if user.expiry_date and user.expiry_date < now:
            flash("Subscription Expired! Please renew to start Algo.")
        else:
            user.algo_status = 'ON'
            db.session.commit()
            flash("Algo Started Successfully!")
    
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/force-close-trade/<int:trade_id>')
def force_close_trade(trade_id):
    trade = AlgoTrade.query.get_or_404(trade_id)
    user_id = session.get('user_id')
    if not user_id or trade.user_id != user_id:
        return "Unauthorized", 403
    
    if trade.status == 'Running':
        trade.status = 'Closed'
        trade.exit_price = trade.entry_price # Marking as break-even on manual close or close at last known
        trade.pnl = 0.0 # Or calculate based on dummy price if available
        
        # 🌟 Forward SELL to Broker if REAL
        user = User.query.get(user_id)
        if user.user_type == 'REAL' and user.is_approved:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=user_id).first()
                webhook_url = broker_conf.webhook_url if broker_conf else user.dhan_webhook_url
                enc_secret = broker_conf.encrypted_secret_key if broker_conf else user.encrypted_secret_key
                
                if enc_secret and webhook_url:
                    secret_key = cipher.decrypt(enc_secret).decode()
                    # Craft a manual SELL alert for the broker
                    manual_alert = {
                        "secret": secret_key,
                        "symbol": trade.symbol,
                        "quantity": trade.quantity,
                        "transactionType": "SELL",
                        "orderType": "MARKET",
                        "productType": "MARGIN",
                        "message": "Manual Force Close from Dashboard"
                    }
                    requests.post(webhook_url, json=manual_alert, timeout=5)
            except Exception as e:
                print(f"Force Close Error: {e}")
        
        db.session.commit()
        flash(f"Trade for {trade.symbol} Force Closed Successfully.")
    
    return redirect(url_for('user_dashboard', user_id=user_id))

# 🌟 USER DASHBOARD ROUTE (With Specific PnL Logic)
@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    session.permanent = True
    session['user_id'] = user_id
    user = User.query.get_or_404(user_id)
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    today_date = now.date()
    remaining_days = (user.expiry_date - now).days if user.expiry_date else 0
    
    # 🌟 Auto Delete old history (Keep only today's detailed history)
    try:
        start_of_today = datetime(today_date.year, today_date.month, today_date.day)
        AlgoTrade.query.filter(AlgoTrade.timestamp < start_of_today).delete()
        db.session.commit()
    except Exception as e:
        print(f"Cleanup Error: {e}")
        db.session.rollback()
    
    # Parse today's trades for the live historical table dynamically
    todays_trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).all()
    parsed_trades = []
    
    for t in todays_trades:
        parsed_trades.append({
            "id": t.id,
            "time": t.timestamp.strftime('%H:%M:%S'),
            "symbol": t.symbol,
            "type": t.trade_type,
            "result": "Target Hit/Sold" if t.status == "Closed" and t.trade_type == "BUY" else ("Running" if t.status == "Running" else "Closed"),
            "pnl": t.pnl,
            "status": t.status,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
        })
        
    pnl_1d = sum(t.pnl for t in todays_trades if t.status == 'Closed')
    
    # Sync today's Live P&L to database so it stays permanently
    today_record = DailyPnL.query.filter_by(date=today_date).first()
    if not today_record:
        db.session.add(DailyPnL(date=today_date, pnl=pnl_1d))
    else:
        today_record.pnl = pnl_1d
    try: db.session.commit()
    except: db.session.rollback()
    
    # 6-Day P&L
    all_daily = DailyPnL.query.order_by(DailyPnL.date.desc()).limit(6).all()
    daily_history = []
    for dp in all_daily:
        daily_history.append({'date': dp.date.strftime("%d %b"), 'pnl': dp.pnl})
        
    pnl_total_6d = sum(dp['pnl'] for dp in daily_history)
    
    # Fetch Broker Config
    broker_config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    
    return render_template('user.html', 
                           user=user, 
                           broker_config=broker_config,
                           remaining_days=max(0, remaining_days),
                           discount_percent=user.personal_discount + 10,
                           pnl_1d=pnl_1d,
                           daily_history=daily_history,
                           pnl_total_6d=pnl_total_6d,
                           parsed_trades=parsed_trades,
                           config=get_admin_config())


# ---------------------------------------------------------
# TRADING LOGIC (The Mechanism)
# ---------------------------------------------------------

@app.route('/tv-webhook', methods=['POST'])
def tv_webhook():
    import json
    alert_data = request.json
    if not alert_data:
        # Fallback to parse it manually if it contains dirty text from TradingView (like {{alert_message}})
        raw_text = request.get_data(as_text=True)
        if raw_text and "{" in raw_text and "}" in raw_text:
            try:
                # Extract string between first '{' and last '}'
                json_str = raw_text[raw_text.find('{'):raw_text.rfind('}')+1]
                alert_data = json.loads(json_str)
            except Exception as e:
                return jsonify({"status": "error", "message": f"Invalid JSON format: {str(e)}"}), 400
        else:
            return jsonify({"status": "error", "message": "No data or not JSON Format"}), 400

    # 1. Parse Alert Fields
    symbol = alert_data.get('symbol', 'UNKNOWN')
    txn_type = str(alert_data.get('transactionType', 'BUY')).upper()
    try:
        price = float(alert_data.get('price', 0.0))
        qty = int(alert_data.get('quantity', 1))
    except (ValueError, TypeError):
        price = 0.0
        qty = 1

    # 2. Sync for ALL Users based on their status
    all_users = User.query.all()
    today_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
    
    trade_executed = False
    
    for u in all_users:
        # 🌟 Check Expiry & Update Status
        if u.expiry_date and u.expiry_date < today_dt:
            if u.algo_status == 'ON':
                u.algo_status = 'OFF'
                square_off_user_trades(u, "Subscription Expired")
                db.session.commit()
            continue

        if u.algo_status == 'OFF' or u.admin_kill_switch:
            continue

        # Handle demo/real trade tracking per user
        if txn_type == "BUY":
            # Avoid duplications if already running
            existing = AlgoTrade.query.filter_by(user_id=u.id, symbol=symbol, status='Running').first()
            if not existing:
                new_trade = AlgoTrade(user_id=u.id, symbol=symbol, quantity=qty, trade_type="BUY", entry_price=price, status="Running", timestamp=today_dt)
                db.session.add(new_trade)
                trade_executed = True
        
        elif txn_type == "SELL":
            active_trades = AlgoTrade.query.filter_by(user_id=u.id, symbol=symbol, status="Running").all()
            if active_trades:
                trade_executed = True
            for at in active_trades:
                exit_val = price if price > 0.0 else at.entry_price
                at.exit_price = exit_val
                at.pnl = (exit_val - at.entry_price) * at.quantity
                at.status = "Closed"
                
                # Update Daily P&L Tracker for this user if needed (can be global/per-user)
                # For now, let's keep DailyPnL as a global metric for the system's performance
                daily_record = DailyPnL.query.filter_by(date=today_dt.date()).first()
                if not daily_record:
                    db.session.add(DailyPnL(date=today_dt.date(), pnl=at.pnl))
                else:
                    daily_record.pnl += at.pnl

        # 3. For REAL users, also forward to Broker
        if u.user_type == 'REAL' and u.is_approved:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                webhook_url = broker_conf.webhook_url if broker_conf else u.dhan_webhook_url
                enc_secret = broker_conf.encrypted_secret_key if broker_conf else u.encrypted_secret_key
                broker_name = broker_conf.broker_name if broker_conf else "Dhan"
                
                if enc_secret and webhook_url:
                    secret_key = cipher.decrypt(enc_secret).decode()
                    
                    # 🌟 TRANSLATOR LOGIC FOR BROKERS 🌟
                    if broker_name.lower() == 'dhan':
                        forward_payload = {
                            "secret": secret_key,
                            "alertType": "multi_leg_order",
                            "order_legs": [
                                {
                                    "transactionType": "B" if txn_type == "BUY" else "S",
                                    "orderType": "MKT",
                                    "quantity": str(qty),
                                    "exchange": "NFO" if ("NIFTY" in symbol.upper() or "BANK" in symbol.upper() or "SENSEX" in symbol.upper()) else "NSE",
                                    "symbol": symbol,
                                    "instrument": "OPT" if ("NIFTY" in symbol.upper() or "BANK" in symbol.upper() or "SENSEX" in symbol.upper()) else "EQ",
                                    "productType": "M"
                                }
                            ]
                        }
                    else:
                        # For Upstox, Zerodha or other standard 3rd party bridges
                        forward_payload = alert_data.copy()
                        forward_payload['secret'] = secret_key
                        
                    # Send request in background thread and capture response
                    def send_to_broker(url, payload, usr_name):
                        try:
                            resp = requests.post(url, json=payload, timeout=5)
                            print(f"[BROKER API] {usr_name} -> Status: {resp.status_code}, Response: {resp.text}", flush=True)
                        except Exception as req_err:
                            print(f"[BROKER HTTP ERROR] {usr_name} -> {req_err}", flush=True)
                            
                    threading.Thread(target=send_to_broker, args=(webhook_url, forward_payload, u.username), daemon=True).start()
            except Exception as e:
                print(f"Forwarding error for {u.username}: {e}", flush=True)

    db.session.commit()

    # 4. Telegram Alert (Send ONLY if a trade was actually executed/closed)
    if trade_executed:
        if txn_type == "BUY":
            target_val = alert_data.get('target', 'N/A')
            sl_val = alert_data.get('sl', 'N/A')
            tg_msg = (
                f"🚀 <b>GVN MASTER ALGO - NEW ENTRY</b> 🚀\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Symbol:</b> <code>{symbol}</code>\n"
                f"💸 <b>Entry Price:</b> <code>₹{price}</code>\n"
                f"✅ <b>Target:</b> <code>₹{target_val}</code>\n"
                f"⛔ <b>Stop Loss:</b> <code>₹{sl_val}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <i>Processed exactly as per GVN Settings</i>"
            )
            send_telegram_msg(tg_msg)
        else:
            status_msg = alert_data.get('status', 'CLOSED (MANUAL)')
            icon = "🛑" if "SL" in status_msg else "🏅" if "Target" in status_msg else "📉"
            tg_msg = (
                f"{icon} <b>GVN ALGO - {status_msg.upper()}</b> {icon}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 <b>Symbol:</b> <code>{symbol}</code>\n"
                f"💸 <b>Exit Price:</b> <code>₹{price}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <i>Trade Successfully Closed by System</i>"
            )
            send_telegram_msg(tg_msg)

    return jsonify({"status": "Signals Processed", "symbol": symbol, "executed": trade_executed}), 200

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    user_id = int(request.form.get('user_id', 0))
    if not user_id:
        return "Invalid User", 400
        
    broker_name = request.form.get('broker_name', 'Dhan')
    webhook_url = request.form.get('webhook_url')
    secret_key = request.form.get('secret_key')
    
    user = User.query.get_or_404(user_id)
    
    broker_config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    if not broker_config:
        broker_config = UserBrokerConfig(user_id=user_id)
        db.session.add(broker_config)
        
    broker_config.broker_name = broker_name
    broker_config.webhook_url = webhook_url
    if secret_key and secret_key != '********':
        broker_config.encrypted_secret_key = cipher.encrypt(secret_key.encode())
    
    db.session.commit()
    return redirect(url_for('user_dashboard', user_id=user_id))

# ---------------------------------------------------------
# DASHBOARD LOGIC (Admin & Global)
# ---------------------------------------------------------

@app.route('/admin-control')
@requires_auth
def admin_dashboard():
    # 🌟 Split Users
    real_users = User.query.filter_by(user_type='REAL').all()
    demo_users = User.query.filter_by(user_type='DEMO').all()
    
    return render_template('admin.html', 
                           real_users=real_users, 
                           demo_users=demo_users, 
                           g_discount=10,
                           config=get_admin_config())

@app.route('/update-settings', methods=['POST'])
@requires_auth
def update_settings():
    config = get_admin_config()
    config.admin_user = request.form.get('admin_user', config.admin_user)
    config.admin_pass = request.form.get('admin_pass', config.admin_pass)
    config.admin_phone = request.form.get('admin_phone', config.admin_phone)
    config.support_number_1 = request.form.get('support_1', config.support_number_1)
    config.support_number_2 = request.form.get('support_2', config.support_number_2)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- OTP RESET FLOW ---
@app.route('/admin-reset', methods=['GET', 'POST'])
def admin_reset():
    if request.method == 'POST':
        phone = request.form.get('phone')
        config = get_admin_config()
        if phone == config.admin_phone:
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            config.reset_otp = otp
            config.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            
            # Simulated SMS send (In reality, use Fast2SMS / Twilio)
            print(f"-------------\n[SMS MOCK] Sent OTP {otp} to {phone}\n-------------")
            
            return f'''
            <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h2>OTP Sent to {phone}</h2>
                <p style="color:red;">(Since real SMS costs money, check your Server Console to see the mock OTP)</p>
                <form action="/admin-verify-otp" method="POST">
                    <input type="text" name="otp" placeholder="Enter 6-digit OTP" required style="padding:10px; width:200px;">
                    <button type="submit" style="padding:10px 20px; background:#28a745; color:white; border:none;">Verify</button>
                </form>
            </div>
            '''
        else:
            return "Invalid Admin Phone Number"
            
    return '''
    <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
        <h2>Forgot Admin Password?</h2>
        <form action="/admin-reset" method="POST">
            <input type="text" name="phone" placeholder="Enter your registered Admin Phone" required style="padding:10px; width:250px;">
            <button type="submit" style="padding:10px 20px; background:#007bff; color:white; border:none;">Send OTP</button>
        </form>
    </div>
    '''

@app.route('/admin-verify-otp', methods=['POST'])
def admin_verify_otp():
    otp = request.form.get('otp')
    config = get_admin_config()
    if config.reset_otp and config.reset_otp == otp and config.otp_expiry > datetime.utcnow():
        return '''
        <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
            <h2>Set New Admin Password</h2>
            <form action="/admin-set-password" method="POST">
                <input type="password" name="new_pass" placeholder="Enter New Password" required style="padding:10px; width:200px;">
                <button type="submit" style="padding:10px 20px; background:#ff9800; color:white; border:none;">Update Password</button>
            </form>
        </div>
        '''
    return "Invalid or Expired OTP. <a href='/admin-reset'>Try again</a>"

@app.route('/admin-set-password', methods=['POST'])
def admin_set_password():
    new_pass = request.form.get('new_pass')
    config = get_admin_config()
    config.admin_pass = new_pass
    config.reset_otp = None # wipe otp
    db.session.commit()
    return "Password updated successfully! <a href='/admin-control'>Go to Admin Login</a>"

@app.route('/approve-user', methods=['POST'])
@requires_auth
def approve_user():
    user_id = int(request.form.get('user_id'))
    plan = request.form.get('plan')
    months = int(request.form.get('months', 1))
    
    user = User.query.get_or_404(user_id)
    user.user_type = 'REAL'
    user.selected_plan = plan
    user.is_approved = True
    
    now = datetime.now()
    if user.expiry_date and user.expiry_date > now:
        user.expiry_date = user.expiry_date + timedelta(days=30 * months)
    else:
        user.expiry_date = now + timedelta(days=30 * months)
        
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin-extend-demo/<int:user_id>')
@requires_auth
def admin_extend_demo(user_id):
    user = User.query.get_or_404(user_id)
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    if user.expiry_date and user.expiry_date > now:
        user.expiry_date = user.expiry_date + timedelta(days=30)
    else:
        user.expiry_date = now + timedelta(days=30)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete-user/<int:user_id>')
@requires_auth
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/toggle-kill-switch/<int:user_id>')
@requires_auth
def toggle_kill_switch(user_id):
    user = User.query.get_or_404(user_id)
    user.admin_kill_switch = not user.admin_kill_switch
    if user.admin_kill_switch:
        square_off_user_trades(user, "Admin Activated Kill Switch")
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/history')
def trade_history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('demo_register'))
    
    history = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).limit(1000).all()
    total_pnl = sum((t.pnl for t in history if t.status == 'Closed'))
    return render_template('history.html', trades=history, total_pnl=total_pnl)

@app.route('/clear-history')
@requires_auth
def clear_history():
    db.session.query(AlgoTrade).delete()
    db.session.commit()
    return redirect(url_for('trade_history'))

import threading
import time

def auto_square_off_task():
    while True:
        try:
            now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            if now.hour == 15 and 28 <= now.minute <= 29:
                with app.app_context():
                    running_trades = AlgoTrade.query.filter_by(status='Running').all()
                    if running_trades:
                        for trade in running_trades:
                            trade.status = 'Closed'
                            trade.exit_price = trade.entry_price
                            trade.pnl = 0.0 # Force closed EOD
                            
                            user = User.query.get(trade.user_id)
                            if user and user.user_type == 'REAL' and user.is_approved:
                                try:
                                    broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
                                    webhook_url = broker_conf.webhook_url if broker_conf else user.dhan_webhook_url
                                    enc_secret = broker_conf.encrypted_secret_key if broker_conf else user.encrypted_secret_key
                                    if enc_secret and webhook_url:
                                        secret_key = cipher.decrypt(enc_secret).decode()
                                        manual_alert = {
                                            "secret": secret_key,
                                            "symbol": trade.symbol,
                                            "quantity": trade.quantity,
                                            "transactionType": "SELL",
                                            "orderType": "MARKET",
                                            "productType": "MARGIN",
                                            "message": "Auto Square-Off at 3:28 PM"
                                        }
                                        requests.post(webhook_url, json=manual_alert, timeout=5)
                                except Exception as e:
                                    pass
                        db.session.commit()
                        send_telegram_msg("⏰ <b>AUTO SQUARE-OFF</b>\nAll open positions forcefully closed at 15:28 IST to manage overnight gap risk.")
        except Exception as e:
            print(f"Auto Square-Off Error: {e}")
        
        # Sleep 60 seconds
        time.sleep(60)

# Start background thread
threading.Thread(target=auto_square_off_task, daemon=True).start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
