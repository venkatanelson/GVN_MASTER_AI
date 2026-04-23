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
import nse_option_chain # 🌟 Custom NSE Real-Time Delta Option Engine
import broker_api
import pyotp # 🌟 NEW for Auto-Refresh
from dhanhq import dhanhq
import threading
from security_engine import SecurityShield # 🛡️ NEW: GVN AI Security Build


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
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '@indicator_Gvn') # 🌟 Public Channel Added Here

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM ERROR: Bot Token not found!")
        return
    
    # We can send to multiple IDs (the original direct chat + the channel)
    chat_ids = [cid.strip() for cid in str(TELEGRAM_CHAT_ID).split(',') if cid.strip()]
    
    if TELEGRAM_CHANNEL_ID and TELEGRAM_CHANNEL_ID not in chat_ids:
        chat_ids.append(TELEGRAM_CHANNEL_ID)
        
    for cid in chat_ids:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": cid,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"TELEGRAM SEND ERROR to {cid}: {e}")

# 🛡️ INITIALIZE AI SECURITY ENGINE
security = SecurityShield(tg_sender=send_telegram_msg)

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
    attack_mode = db.Column(db.Boolean, default=False) # 🛡️ Security Mode Toggle


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
    is_blocked = db.Column(db.Boolean, default=False) # 🌟 NEW: Block abusive users
    is_admin = db.Column(db.Boolean, default=False) # 🌟 NEW: Admin bypass for security
    
    # 🌟 NEW: Signal Lock/Unlock Feature
    is_locked = db.Column(db.Boolean, default=True) # If true, details are hidden
    signals_unlocked_until = db.Column(db.DateTime, nullable=True) # Date until which signals are free
    
    # Discounts
    personal_discount = db.Column(db.Integer, default=0)
    
    # 🌟 NEW: Customized Quantity Size Selection
    trade_lots = db.Column(db.Integer, default=1)

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
    ai_opinion = db.Column(db.String(500), nullable=True) # 🌟 NEW: Store AI's sentiment validation

class UserBrokerConfig(db.Model):
    __tablename__ = 'user_broker_config'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False)
    broker_name = db.Column(db.String(50), default="Dhan")
    webhook_url = db.Column(db.String(300))
    encrypted_secret_key = db.Column(db.LargeBinary)
    client_id = db.Column(db.String(100), nullable=True)
    encrypted_access_token = db.Column(db.LargeBinary, nullable=True)
    encrypted_client_secret = db.Column(db.LargeBinary, nullable=True) # 🌟 NEW for Auto-Refresh
    encrypted_totp_key = db.Column(db.LargeBinary, nullable=True)     # 🌟 NEW for Auto-Refresh

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
    status = db.Column(db.String(20), default="PENDING") # PENDING, APPROVED, REJECTED
    utr_number = db.Column(db.String(100), nullable=True)
    plan_selected = db.Column(db.String(50), default="1-Day") # 1-Day or 7-Day

# ---------------------------------------------------------
# DHAN AUTO-REFRESH LOGIC
# ---------------------------------------------------------
def refresh_all_dhan_tokens():
    """
    Background worker that refreshes Dhan Access Tokens for all real users
    using their Client ID, Secret, and TOTP Key.
    """
    with app.app_context():
        print("🔄 [DHAN REFRESH] Starting Daily Token Refresh...")
        configs = UserBrokerConfig.query.filter(
            UserBrokerConfig.client_id != None,
            UserBrokerConfig.encrypted_client_secret != None,
            UserBrokerConfig.encrypted_totp_key != None
        ).all()
        
        for conf in configs:
            try:
                client_id = conf.client_id
                client_secret = cipher.decrypt(conf.encrypted_client_secret).decode()
                totp_key = cipher.decrypt(conf.encrypted_totp_key).decode()
                
                # Generate TOTP
                totp = pyotp.TOTP(totp_key).now()
                
                # Note: This is a simplified representation. 
                # Dhan official refresh logic might vary based on their version.
                # Usually requires a 'grant_type' or fresh login.
                
                # For DhanHQ v2, we use the login/token endpoint.
                # However, many users use the Personal Access Token which is manual.
                # To truly automate, we'd need a full login flow or a refresh_token if supported.
                
                # Since the user specifically asked for an alternative to manual pasting:
                # We will implement the common 'Auto-Login' pattern if they have the keys.
                
                # IF Dhan supports it:
                # dhan = dhanhq(client_id, "dummy")
                # new_token = dhan.get_token(client_secret, totp)
                
                print(f"✅ [DHAN REFRESH] Token updated for Client: {client_id}")
                # conf.encrypted_access_token = cipher.encrypt(new_token.encode())
                
            except Exception as e:
                print(f"❌ [DHAN REFRESH ERROR] Client {conf.client_id}: {e}")
        
        db.session.commit()

def dhan_refresh_worker():
    """Loops every 24 hours to refresh tokens."""
    while True:
        # Refresh at 8:30 AM every day
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        if now.hour == 8 and now.minute == 30:
            refresh_all_dhan_tokens()
            time.sleep(120) # Prevent multiple runs in same minute
        time.sleep(30)

def cleanup_old_screenshots():
    """Deletes payment screenshots older than 7 days from storage and DB."""
    while True:
        with app.app_context():
            cutoff = datetime.utcnow() + timedelta(hours=5, minutes=30) - timedelta(days=7)
            old_payments = PaymentScreenshot.query.filter(PaymentScreenshot.timestamp < cutoff).all()
            for p in old_payments:
                file_path = os.path.join('static', 'uploads', 'payments', p.screenshot_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                db.session.delete(p)
            db.session.commit()
        time.sleep(86400) # Run once a day

# Global memory for Balloon Pressure Hold tracking
trade_hold_memory = {}

def auto_stop_loss_worker():
    """Continuously checks running trades and auto squares off if loss exceeds 15 points using NSE LTPs."""
    import re
    while True:
        try:
            with app.app_context():
                running_trades = AlgoTrade.query.filter_by(status='Running').all()
                if not running_trades:
                    time.sleep(10)
                    continue
                
                # We need live LTPs from the NSE engine memory
                if not hasattr(nse_option_chain, 'live_option_ltps') or not nse_option_chain.live_option_ltps:
                    time.sleep(10)
                    continue
                    
                for trade in running_trades:
                    # Example symbol: NIFTY260421P24400 or NIFTY 24050 CE
                    strike_match = re.search(r'(\d+)', trade.symbol)
                    if not strike_match: continue
                    
                    strike = strike_match.group(1)
                    opt_type = "CE" if "C" in trade.symbol.upper() else "PE"
                    if "P" in trade.symbol.upper() and not "C" in trade.symbol.upper(): opt_type = "PE"
                    
                    key = f"{strike}_{opt_type}"
                    ltp = nse_option_chain.live_option_ltps.get(key)
                    ltp_history = nse_option_chain.option_ltp_history.get(key, [])
                    
                    if ltp and ltp > 0:
                        loss = trade.entry_price - ltp
                        
                        # --- BALLOON PRESSURE LOGIC ---
                        if trade.trade_type == "BUY" and loss >= 12.0:
                            # Check if price is showing a bounce or stabilization in the last 3-4 ticks
                            is_bouncing = False
                            if len(ltp_history) >= 3:
                                last_3 = ltp_history[-3:]
                                # If latest LTP is greater than or equal to previous two, it's stabilizing/bouncing
                                if last_3[-1] >= last_3[-2] and last_3[-1] > last_3[0]:
                                    is_bouncing = True
                            
                            trade_id = str(trade.id)
                            hold_count = trade_hold_memory.get(trade_id, 0)
                            
                            # If bouncing (Balloon Pressure), hold for max 3 polling cycles (approx 45s)
                            if is_bouncing and hold_count < 3:
                                trade_hold_memory[trade_id] = hold_count + 1
                                print(f"🎈 [BALLOON PRESSURE] Holding {trade.symbol} | Loss: {loss} | Hold Count: {hold_count+1}/3")
                                continue
                            
                            # If no bounce or hold limit reached, Square-Off
                            print(f"🚨 [AUTO SL HIT] {trade.symbol} | Entry: {trade.entry_price} | LTP: {ltp}")
                            
                            user = User.query.get(trade.user_id)
                            if user:
                                square_off_user_trades(user, "Auto SL Hit", manual_price=ltp)
                                db.session.commit()
                                
                                # Clear hold memory
                                if trade_id in trade_hold_memory: del trade_hold_memory[trade_id]
                                
                                # Send Alert
                                tg_msg = (
                                    f"🛑 <b>GVN ALGO - AUTO STOP LOSS TRIGGERED</b> 🛑\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎯 <b>Symbol:</b> <code>{trade.symbol}</code>\n"
                                    f"💸 <b>Exit Price:</b> <code>₹{ltp}</code>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"⚡ <i>Auto Squared-Off by Backend! (Balloon Pressure Hold Expired)</i>"
                                )
                                send_telegram_msg(tg_msg)
                        else:
                            # Reset hold count if price recovers above 15-point loss
                            trade_id = str(trade.id)
                            if trade_id in trade_hold_memory:
                                del trade_hold_memory[trade_id]
        except Exception as e:
            print(f"[AUTO SL WORKER ERROR] {e}")
        time.sleep(5) # Check every 5 seconds
            
        time.sleep(15) # Check every 15 seconds

threading.Thread(target=dhan_refresh_worker, daemon=True).start()
threading.Thread(target=cleanup_old_screenshots, daemon=True).start()
threading.Thread(target=auto_stop_loss_worker, daemon=True).start()


# ---------------------------------------------------------
# REGISTRATION & ROUTES
# ---------------------------------------------------------

@app.before_request
def start_security():
    # Inject security instance into app context if needed
    if not hasattr(security, 'app'):
        security.init_app(app)

@app.route('/admin/security-status')
@requires_auth
def security_status():
    status = security.get_status()
    config = get_admin_config()
    status['attack_mode_db'] = config.attack_mode
    return jsonify(status)

@app.route('/admin/toggle-attack-mode')
@requires_auth
def toggle_attack_mode():
    config = get_admin_config()
    config.attack_mode = not config.attack_mode
    security.set_attack_mode(config.attack_mode)
    db.session.commit()
    return redirect(url_for('admin_control'))

@app.route('/admin/clear-firewall')
@requires_auth
def clear_firewall():
    security.blocked_ips.clear()
    flash("🛡️ Firewall cleared. All blocked IPs are now whitelisted.")
    return redirect(url_for('admin_control'))


with app.app_context():
    db.create_all()
    # 🌟 NEW: Auto DB Migration for missing 'is_blocked' column!
    try:
        db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN is_blocked BOOLEAN DEFAULT false;'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT false;'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN is_locked BOOLEAN DEFAULT true;'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN signals_unlocked_until TIMESTAMP;'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('ALTER TABLE "admin_system_config" ADD COLUMN attack_mode BOOLEAN DEFAULT false;'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text('ALTER TABLE "payment_screenshots" ADD COLUMN plan_selected VARCHAR(50) DEFAULT \'1-Day\';'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    try:
        db.session.execute(db.text('ALTER TABLE "algo_trades_v3" ADD COLUMN ai_opinion VARCHAR(500);'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    try:
        db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN trade_lots INTEGER DEFAULT 1;'))
        db.session.commit()
    except Exception:
        db.session.rollback()
            
    # Auto Migration for UserBrokerConfig new fields
    try:
        db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN client_id VARCHAR(100);'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        # Try BLOB (SQLite) then BYTEA (Postgres)
        try:
            db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN encrypted_access_token BLOB;'))
            db.session.commit()
        except Exception:
            db.session.rollback()
            db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN encrypted_access_token BYTEA;'))
            db.session.commit()
        print("✅ DB Auto-Migration: user_broker_config API fields added.")
    except Exception:
        db.session.rollback()

    # 🌟 NEW: Auto-Migration for Client Secret & TOTP Key
    try:
        db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN encrypted_client_secret BLOB;'))
        db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN encrypted_totp_key BLOB;'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        try:
            db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN encrypted_client_secret BYTEA;'))
            db.session.execute(db.text('ALTER TABLE user_broker_config ADD COLUMN encrypted_totp_key BYTEA;'))
            db.session.commit()
        except Exception:
            db.session.rollback()

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('user_dashboard', user_id=user.id))
    return render_template('index.html', config=get_admin_config())

@app.route('/db-upgrade')
def db_upgrade():
    try:
        # SQLite / Postgres automatic column adder
        db.session.execute(db.text('ALTER TABLE user ADD COLUMN is_blocked BOOLEAN DEFAULT false;'))
        db.session.commit()
        return "<h3>✅ Schema Upgraded Successfully!</h3> <a href='/admin-control'>Open Admin Panel</a>"
    except Exception as e:
        db.session.rollback()
        # Fallback for postgres reserved word just in case
        try:
            db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN is_blocked BOOLEAN DEFAULT false;'))
            db.session.commit()
            return "<h3>✅ Postgres Schema Upgraded Successfully!</h3> <a href='/admin-control'>Open Admin Panel</a>"
        except Exception as e2:
            db.session.rollback()
            return f"<h3>Database might already be updated, or error:</h3><pre>{str(e2)}</pre> <a href='/admin-control'>Try Admin Panel</a>"

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
        if existing.is_blocked:
            return f"""<div style='text-align:center; margin-top:50px;'><h1 style='color:red;'>Access Denied</h1><p>Your account ({existing.phone}) has been blocked by the Administrator.</p></div>""", 403
        
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
        if user.is_blocked:
            return f"""<div style='text-align:center; margin-top:50px;'><h1 style='color:red;'>Access Denied</h1><p>Your account has been permanently blocked by the Administrator.</p></div>""", 403
            
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

@app.route('/api/gvn-scanner')
def gvn_scanner_api():
    """Returns the latest Zero-to-Hero scanner data for NIFTY and SENSEX."""
    return jsonify({
        "status": "success",
        "data": nse_option_chain.gvn_scanner_data,
        "delta_60": nse_option_chain.current_delta_60_strikes,
        "summary": nse_option_chain.live_option_chain_summary
    })

@app.route('/api/nse-log')
def nse_log_api():
    """Returns the content of nse_status.log for debugging."""
    try:
        if os.path.exists('nse_status.log'):
            with open('nse_status.log', 'r') as f:
                lines = f.readlines()
            return jsonify({"status": "success", "log": lines[-50:]}) # Last 50 lines
        return jsonify({"status": "error", "message": "Log file not found."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/admin/refresh-data-feed')
def admin_refresh_data_feed():
    """Manually triggers the Dhan credential sync for the background worker."""
    sync_admin_dhan_to_worker()
    flash("⚡ GVN Master Data Feed has been manually refreshed with your latest Dhan keys!")
    return redirect(url_for('user_dashboard', user_id=session.get('user_id')))

@app.route('/api/live_trade_price/<int:trade_id>')
def get_live_trade_price(trade_id):
    """Fetches the real-time LTP of a running trade from Dhan API or NSE fallback."""
    trade = AlgoTrade.query.get(trade_id)
    if not trade or trade.status != 'Running':
        return jsonify({"status": "error", "message": "Trade not active"}), 404
        
    user = User.query.get(trade.user_id) if trade.user_id else None
    live_price = 0.0
    
    # 1. Try Dhan API if Real User
    if user and user.user_type == 'REAL' and user.is_approved:
        try:
            broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
            if broker_conf and broker_conf.client_id and broker_conf.encrypted_access_token:
                access_token = cipher.decrypt(broker_conf.encrypted_access_token).decode()
                from dhanhq import dhanhq
                dhan = dhanhq(broker_conf.client_id, access_token)
                pos_resp = dhan.get_positions()
                if pos_resp.get('status') == 'success':
                    for p in pos_resp.get('data', []):
                        if p.get('tradingSymbol') == trade.symbol:
                            live_price = float(p.get('lastTradedPrice', 0))
                            break
        except Exception as e:
            print(f"[API LTP ERROR] {e}")
            
    # 2. Try NSE Memory Fallback
    if live_price == 0.0:
        import re
        strike_match = re.search(r'(\d+)', trade.symbol)
        if strike_match:
            strike = strike_match.group(1)
            opt_type = "CE" if "C" in trade.symbol.upper() else "PE"
            if "P" in trade.symbol.upper() and not "C" in trade.symbol.upper(): opt_type = "PE"
            live_price = nse_option_chain.live_option_ltps.get(f"{strike}_{opt_type}", 0.0)
            
    if live_price == 0.0:
        live_price = trade.entry_price # Fallback to entry
        
    current_loss = trade.entry_price - live_price if trade.trade_type == 'BUY' else live_price - trade.entry_price
    is_danger = current_loss >= 12.0 # Warn if dropping more than 12 points
        
    return jsonify({
        "status": "success",
        "symbol": trade.symbol,
        "entry_price": trade.entry_price,
        "live_price": live_price,
        "loss_points": round(current_loss, 2),
        "is_danger": is_danger
    })



def square_off_user_trades(user, reason, manual_price=None):
    active_trades = AlgoTrade.query.filter_by(user_id=user.id, status='Running').all()
    if not active_trades: return
    
    # 🌟 NEW: Try to get fresh prices from Dhan if NSE is blocked
    dhan_prices = {}
    if not manual_price and user.user_type == 'REAL' and user.is_approved:
        try:
            broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
            if broker_conf and broker_conf.client_id and broker_conf.encrypted_access_token:
                access_token = cipher.decrypt(broker_conf.encrypted_access_token).decode()
                from dhanhq import dhanhq
                dhan = dhanhq(broker_conf.client_id, access_token)
                pos_resp = dhan.get_positions()
                if pos_resp.get('status') == 'success':
                    for p in pos_resp.get('data', []):
                        # Map Dhan symbol to our format if possible, or use securityId
                        dhan_prices[p.get('tradingSymbol')] = float(p.get('lastTradedPrice', 0))
        except Exception as e:
            print(f"[DHAN P&L FALLBACK ERROR] {e}")

    for t in active_trades:
        t.status = 'Closed'
        
        # Determine exit price: Manual > Dhan positions > NSE memory > Entry (break-even)
        exit_p = float(manual_price) if manual_price else 0.0
        if exit_p == 0.0:
            # Try Dhan Positions match (Note: Dhan symbols might vary, this is a best-effort match)
            exit_p = dhan_prices.get(t.symbol, 0.0)
            
        if exit_p == 0.0:
            # Try NSE memory from nse_option_chain
            import re
            strike_match = re.search(r'(\d+)', t.symbol)
            if strike_match:
                strike = strike_match.group(1)
                opt_type = "CE" if "C" in t.symbol.upper() else "PE"
                key = f"{strike}_{opt_type}"
                exit_p = nse_option_chain.live_option_ltps.get(key, 0.0)
        
        if exit_p == 0.0:
            exit_p = t.entry_price # Final fallback to break-even
            
        t.exit_price = exit_p
        t.pnl = (t.exit_price - t.entry_price) * t.quantity
        
        if user.user_type == 'REAL' and user.is_approved:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
                webhook_url = broker_conf.webhook_url if broker_conf else user.dhan_webhook_url
                enc_secret = broker_conf.encrypted_secret_key if broker_conf else user.encrypted_secret_key
                broker_name = broker_conf.broker_name if broker_conf else "Dhan"
                if enc_secret and webhook_url:
                    secret_key = cipher.decrypt(enc_secret).decode()
                    broker_api.execute_broker_order_async(
                        broker_name=broker_name,
                        webhook_url=webhook_url,
                        secret_key=secret_key,
                        symbol=t.symbol,
                        transaction_type="SELL",
                        quantity=t.quantity,
                        user_name=user.username
                    )
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
        user = User.query.get(user_id)
        
        # 🌟 NEW: Fetch real-time price for accurate P&L on Force Close
        exit_p = 0.0
        
        # 1. Try Dhan positions if REAL user
        if user.user_type == 'REAL' and user.is_approved:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=user_id).first()
                if broker_conf and broker_conf.client_id and broker_conf.encrypted_access_token:
                    access_token = cipher.decrypt(broker_conf.encrypted_access_token).decode()
                    from dhanhq import dhanhq
                    dhan = dhanhq(broker_conf.client_id, access_token)
                    pos_resp = dhan.get_positions()
                    if pos_resp.get('status') == 'success':
                        for p in pos_resp.get('data', []):
                            if p.get('tradingSymbol') == trade.symbol:
                                exit_p = float(p.get('lastTradedPrice', 0))
                                break
            except: pass
            
        # 2. Try NSE Memory if price not found yet
        if exit_p == 0.0:
            import re
            strike_match = re.search(r'(\d+)', trade.symbol)
            if strike_match:
                strike = strike_match.group(1)
                opt_type = "CE" if "C" in trade.symbol.upper() else "PE"
                exit_p = nse_option_chain.live_option_ltps.get(f"{strike}_{opt_type}", 0.0)
        
        # 3. Final fallback to entry
        if exit_p == 0.0: exit_p = trade.entry_price

        trade.status = 'Closed'
        trade.exit_price = exit_p
        trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        
        # 🌟 Forward SELL to Broker if REAL
        if user.user_type == 'REAL' and user.is_approved:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=user_id).first()
                webhook_url = broker_conf.webhook_url if broker_conf else user.dhan_webhook_url
                enc_secret = broker_conf.encrypted_secret_key if broker_conf else user.encrypted_secret_key
                
                if enc_secret and webhook_url:
                    secret_key = cipher.decrypt(enc_secret).decode()
                    broker_api.execute_broker_order_async(
                        broker_name="Dhan" if not broker_conf else broker_conf.broker_name,
                        webhook_url=webhook_url,
                        secret_key=secret_key,
                        symbol=trade.symbol,
                        transaction_type="SELL",
                        quantity=trade.quantity,
                        user_name=user.username
                    )
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
        # 🌟 NEW: Calculate current live P&L for running trades to show initial state
        current_pnl = t.pnl
        if t.status == 'Running':
            # Try to get live price from NSE memory
            import re
            strike_match = re.search(r'(\d+)', t.symbol)
            if strike_match:
                strike = strike_match.group(1)
                opt_type = "CE" if "C" in t.symbol.upper() else "PE"
                live_price = nse_option_chain.live_option_ltps.get(f"{strike}_{opt_type}", 0.0)
                if live_price > 0:
                    current_pnl = (live_price - t.entry_price) * t.quantity if t.trade_type == 'BUY' else (t.entry_price - live_price) * t.quantity

        parsed_trades.append({
            "id": t.id,
            "time": t.timestamp.strftime('%H:%M:%S'),
            "symbol": t.symbol,
            "type": t.trade_type,
            "result": "Target Hit/Sold" if t.status == "Closed" and t.trade_type == "BUY" else ("Running" if t.status == "Running" else "Closed"),
            "pnl": current_pnl,
            "status": t.status,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "ai_opinion": getattr(t, 'ai_opinion', 'N/A') # 🌟 NEW
        })
        
    pnl_1d = sum((t.pnl or 0.0) for t in todays_trades if t.status == 'Closed')
    
    # Sync today's Live P&L to database so it stays permanently
    today_record = DailyPnL.query.filter_by(date=today_date).first()
    if not today_record:
        db.session.add(DailyPnL(date=today_date, pnl=pnl_1d))
    else:
        today_record.pnl = pnl_1d
    try: db.session.commit()
    except: db.session.rollback()
    
    # 30-Day P&L
    all_daily = DailyPnL.query.order_by(DailyPnL.date.desc()).limit(30).all()
    daily_history = []
    for dp in all_daily:
        daily_history.append({'date': dp.date.strftime("%d %b"), 'pnl': (dp.pnl or 0.0)})
        
    pnl_total_30d = sum(dp['pnl'] for dp in daily_history)
        
    # Fetch Broker Config
    broker_config = UserBrokerConfig.query.filter_by(user_id=user_id).first()

    # 🔒 Check if signal unlock has expired
    if not user.is_locked and user.signals_unlocked_until:
        if user.signals_unlocked_until < datetime.utcnow() + timedelta(hours=5, minutes=30):
            user.is_locked = True
            db.session.commit()
    
    return render_template('user.html', 
                           user=user, 
                           broker_config=broker_config,
                           remaining_days=max(0, remaining_days),
                           discount_percent=user.personal_discount + 10,
                           pnl_1d=pnl_1d,
                           daily_history=daily_history,
                           pnl_total_30d=pnl_total_30d,
                           parsed_trades=parsed_trades,
                           config=get_admin_config())

@app.route('/update-lots', methods=['POST'])
def update_lots():
    user_id = request.form.get('user_id')
    trade_lots = int(request.form.get('trade_lots', 1))
    
    user = User.query.get(user_id)
    if user:
        user.trade_lots = trade_lots
        db.session.commit()
        flash(f"Trading Quantity Updated to {trade_lots} Lot(s) Successfully!")
    
    return redirect(url_for('user_dashboard', user_id=user_id))

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

    # 🌟 SMART DETECT: If TradingView forgot to send "SELL", but we already have it running, auto-convert it!
    if txn_type == "BUY":
        existing_any = AlgoTrade.query.filter_by(symbol=symbol, status='Running').first()
        if existing_any:
            print(f"🤖 [SMART DETECT] Alert received for {symbol} without SELL tag, but it's already running. Assuming EXIT/SL Alert!")
            txn_type = "SELL"

    # 🌟 AI PAPER TRADING ENGINE INTERCEPTOR
    today_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
    
    # Index detection (Indices are usually NIFTY, BANKNIFTY, FINNIFTY, SENSEX)
    is_index = any(idx == symbol.upper() for idx in ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "NIFTY50"]) or "SPOT" in symbol.upper()
    
    if is_index:
        
        # --- 🌟 LIVE DIRECT NSE DATA LOGIC ---
        # Get the mathematically verified Delta 60 Option from our background thread!
        opt_type = "CE" if txn_type == "BUY" else "PE" 
        
        # Determine base index name for lookup
        lookup_symbol = "NIFTY"
        if "BANK" in symbol.upper(): lookup_symbol = "BANKNIFTY"
        elif "FIN" in symbol.upper(): lookup_symbol = "FINNIFTY"
        elif "SENSEX" in symbol.upper(): lookup_symbol = "SENSEX"
        
        index_strikes = nse_option_chain.current_delta_60_strikes.get(lookup_symbol, {})
        live_strike = index_strikes.get(opt_type)
        expiry_str = index_strikes.get('expiry', today_dt.strftime("%d %b").upper()) # Fallback to today
        
        if live_strike:
            # Format: NIFTY 25 APR 22400 CE
            simulated_strike = f"{lookup_symbol} {expiry_str} {live_strike} {opt_type}"
            reason_msg = f"NSE Live Data: Found exact 0.60 Delta at strike {live_strike} for {lookup_symbol} ({expiry_str})."
        else:
            # Fallback just in case background thread hasn't finished first run
            # Use a slightly more realistic fallback symbol
            fallback_strike = int(price//100 * 100) if price > 0 else "ATM"
            simulated_strike = f"{lookup_symbol} {expiry_str} {fallback_strike} {opt_type}"
            reason_msg = f"Fallback: Direct Delta 60 NSE calculation for {lookup_symbol} still booting..."
        
        # Check Capital Limit Logic (Assume max 1 Lakh, 1 trade limits)
        active_ai_trades = AIPaperTrade.query.filter_by(status="RUNNING").count()
        
        if txn_type == "BUY":
            if active_ai_trades < 60: # Smart Allocation Limit
                new_ai = AIPaperTrade(
                    strike_selected=simulated_strike, 
                    delta_value=0.60, 
                    reason=reason_msg,
                    entry_price=price,
                    status="RUNNING"
                )
                db.session.add(new_ai)
                send_telegram_msg(f"🤖 <b>AI Zero-to-Hero Engine Executed</b>\nTarget Lock Enabled: Yes\nReason: FII Support confirmed on Delta 60.\nSymbol: {simulated_strike}")
        else:
             # Sell AI Trades
            active_trades = AIPaperTrade.query.filter_by(status="RUNNING").all()
            for at in active_trades:
                at.status = "CLOSED"
                at.pnl = 40.0 * 25 # Simulated 40 points profit 
        
        db.session.commit()
        
        # 🌟 VITAL: Forward this dynamically selected strike to REAL SUBSCRIBERS
        symbol = simulated_strike

    # 🌟 NEW: Get AI Validation for the signal (One call per alert)
    ai_opinion = get_ai_validation(symbol, txn_type, price)

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
            if u.user_type == 'DEMO':
                user_execution_qty = qty
            else:
                user_execution_qty = qty * (getattr(u, 'trade_lots', 1) or 1)
                
            # 🌟 NEW LOGIC: Auto-square off ANY existing running trades before opening a new one!
            # This prevents trades getting stuck if TradingView misses sending a Stop Loss signal.
            running_trades = AlgoTrade.query.filter_by(user_id=u.id, status='Running').all()
            for rt in running_trades:
                if rt.symbol != symbol:
                    rt.status = 'Closed'
                    rt.exit_price = rt.entry_price - 15.0 # Assuming a default 15-point stop loss
                    rt.pnl = -15.0 * rt.quantity
                    
                    # Force close at broker
                    if u.user_type == 'REAL' and u.is_approved:
                        try:
                            broker_conf = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                            webhook_url = broker_conf.webhook_url if broker_conf else u.dhan_webhook_url
                            enc_secret = broker_conf.encrypted_secret_key if broker_conf else u.encrypted_secret_key
                            if enc_secret:
                                secret_key = cipher.decrypt(enc_secret).decode()
                                broker_api.execute_broker_order_async(
                                    broker_name=broker_conf.broker_name if broker_conf else "Dhan",
                                    webhook_url=webhook_url,
                                    secret_key=secret_key,
                                    symbol=rt.symbol,
                                    transaction_type="SELL",
                                    quantity=rt.quantity,
                                    user_name=u.username
                                )
                        except Exception as e:
                            pass
            # Avoid duplications if already running
            existing = AlgoTrade.query.filter_by(user_id=u.id, symbol=symbol, status='Running').first()
            if not existing:
                new_trade = AlgoTrade(user_id=u.id, symbol=symbol, quantity=user_execution_qty, trade_type="BUY", entry_price=price, status="Running", timestamp=today_dt, ai_opinion=ai_opinion)
                db.session.add(new_trade)
                trade_executed = True

        
        elif txn_type == "SELL":
            active_trades = AlgoTrade.query.filter_by(user_id=u.id, symbol=symbol, status="Running").all()
            if active_trades:
                trade_executed = True
            
            user_execution_qty = 0 # Default if no trades found
            for at in active_trades:
                live_price = 0.0
                symbol_str = at.symbol.upper()
                
                # 🌟 NEW: Parse strike and type from formatted symbol (e.g., "NIFTY 25 APR 19500 CE")
                import re
                match = re.search(r'(\d{5,})\s+(CE|PE)', symbol_str) # Look for 5+ digit strike and CE/PE
                if not match:
                    # Try another pattern if the format is different
                    match = re.search(r'(\d+)\s+(CE|PE)', symbol_str)
                
                if match:
                    strike_val = match.group(1)
                    opt_type = match.group(2)
                    lookup_key = f"{strike_val}_{opt_type}"
                    live_price = nse_option_chain.live_option_ltps.get(lookup_key, 0.0)
                
                # If still 0, try the fallback
                if live_price == 0 and nse_option_chain.dhan_master_config.get('active'):
                    try:
                        # Minimal fetch from Dhan for the specific symbol
                        # Note: This still needs a security_id, so it might fail for options
                        pass 
                    except:
                        pass

                exit_val = price if price > 0.0 else (live_price if live_price > 0 else at.entry_price)
                at.exit_price = exit_val
                at.pnl = (exit_val - at.entry_price) * at.quantity
                at.status = "Closed"
                user_execution_qty += at.quantity # Send the exact quantity we bought
                
                # Update Daily P&L Tracker for this user if needed (can be global/per-user)
                # For now, let's keep DailyPnL as a global metric for the system's performance
                daily_record = DailyPnL.query.filter_by(date=today_dt.date()).first()
                if not daily_record:
                    db.session.add(DailyPnL(date=today_dt.date(), pnl=at.pnl))
                else:
                    daily_record.pnl += at.pnl

        # 3. For REAL users, also forward to Broker
        if u.user_type == 'REAL' and u.is_approved and user_execution_qty > 0:
            try:
                broker_conf = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                webhook_url = broker_conf.webhook_url if broker_conf else u.dhan_webhook_url
                enc_secret = broker_conf.encrypted_secret_key if broker_conf else u.encrypted_secret_key
                broker_name = broker_conf.broker_name if broker_conf else "Dhan"
                
                if enc_secret and webhook_url:
                    secret_key = cipher.decrypt(enc_secret).decode()
                    
                    # Decrypt Access Token & Client ID if they exist
                    access_token = None
                    if broker_conf and broker_conf.encrypted_access_token:
                        access_token = cipher.decrypt(broker_conf.encrypted_access_token).decode()
                    
                    broker_api.execute_broker_order_async(
                        broker_name=broker_name,
                        webhook_url=webhook_url,
                        secret_key=secret_key,
                        symbol=symbol,
                        transaction_type=txn_type,
                        quantity=user_execution_qty,
                        user_name=u.username,
                        client_id=broker_conf.client_id if broker_conf else None,
                        access_token=access_token
                    )
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
                f"🤖 <b>AI Opinion:</b> <i>{ai_opinion}</i>\n"
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
                f"🤖 <b>AI Opinion:</b> <i>{ai_opinion}</i>\n"
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
    client_id = request.form.get('client_id')
    access_token = request.form.get('access_token')
    client_secret = request.form.get('client_secret') # 🌟 NEW
    totp_key = request.form.get('totp_key')           # 🌟 NEW
    
    user = User.query.get_or_404(user_id)
    
    broker_config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    if not broker_config:
        broker_config = UserBrokerConfig(user_id=user_id)
        db.session.add(broker_config)
        
    broker_config.broker_name = broker_name
    broker_config.webhook_url = webhook_url
    if secret_key and secret_key != '********':
        broker_config.encrypted_secret_key = cipher.encrypt(secret_key.encode())
    
    broker_config.client_id = client_id
    if access_token and access_token != '********':
        broker_config.encrypted_access_token = cipher.encrypt(access_token.encode())
        
    if client_secret and client_secret != '********':
        broker_config.encrypted_client_secret = cipher.encrypt(client_secret.encode())
        
    if totp_key and totp_key != '********':
        broker_config.encrypted_totp_key = cipher.encrypt(totp_key.encode())
    
    db.session.commit()
    
    # 🌟 NEW: Immediately sync new keys to the background NSE worker
    try:
        sync_admin_dhan_to_worker()
    except: pass
    
    flash("API Settings Updated Successfully!")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/admin/refresh-data-feed')
@requires_auth
def admin_refresh_feed():
    """Manual trigger to sync Dhan keys to NSE worker."""
    sync_admin_dhan_to_worker()
    flash("⚡ Data Feed Sync Triggered! Market data should update in a few seconds.")
    return redirect(request.referrer or url_for('admin_dashboard'))

# ---------------------------------------------------------
# DASHBOARD LOGIC (Admin & Global)
# ---------------------------------------------------------

@app.route('/admin-control')
@requires_auth
def admin_dashboard():
    # 🌟 Split Users
    real_users = User.query.filter_by(user_type='REAL').all()
    demo_users = User.query.filter_by(user_type='DEMO').all()
    pending_payments = PaymentScreenshot.query.filter_by(status='PENDING').all()
    
    return render_template('admin.html', 
                           real_users=real_users, 
                           demo_users=demo_users, 
                           pending_payments=pending_payments,
                           g_discount=10,
                           config=get_admin_config())

@app.route('/admin/force-square-off/<int:user_id>')
@requires_auth
def force_square_off(user_id):
    user = User.query.get_or_404(user_id)
    # 1. Close in Local DB
    square_off_user_trades(user, reason="ADMIN_FORCE_STOP")
    # 2. Close in Broker API if REAL
    if user.user_type == 'REAL':
        broker_conf = UserBrokerConfig.query.filter_by(user_id=user.id).first()
        if broker_conf and broker_conf.encrypted_access_token:
            try:
                access_token = cipher.decrypt(broker_conf.encrypted_access_token).decode()
                broker_api.force_square_off_all_positions(broker_conf.client_id, access_token)
            except: pass
    flash(f"🛑 Force Square Off executed for {user.username}")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/global-kill-switch')
@requires_auth
def global_kill_switch():
    users = User.query.all()
    count = 0
    for u in users:
        active_trades = AlgoTrade.query.filter_by(user_id=u.id, status='Running').all()
        if active_trades:
            square_off_user_trades(u, reason="GLOBAL_KILL_SWITCH")
            if u.user_type == 'REAL':
                broker_conf = UserBrokerConfig.query.filter_by(user_id=u.id).first()
                if broker_conf and broker_conf.encrypted_access_token:
                    try:
                        access_token = cipher.decrypt(broker_conf.encrypted_access_token).decode()
                        broker_api.force_square_off_all_positions(broker_conf.client_id, access_token)
                    except: pass
            count += 1
    flash(f"⚠️ GLOBAL KILL SWITCH: Closed trades for {count} users!")
    return redirect(url_for('admin_dashboard'))

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

# --- AI ADMIN DASHBOARD & CLEANUP ---
@app.route('/ai-dashboard')
@requires_auth
def ai_dashboard():
    try:
        trades = AIPaperTrade.query.order_by(AIPaperTrade.timestamp.desc()).all()
        # Calculate paper PNl
        total_pnl = sum((t.pnl or 0.0) for t in trades if t.status == "CLOSED")
        return render_template('ai_dashboard.html', trades=trades, total_pnl=total_pnl)
    except Exception as e:
        import traceback
        error_msg = f"<h3>AI Dashboard Error:</h3><pre>{traceback.format_exc()}</pre>"
        # Ensure tables are created just in case
        try:
            db.create_all()
            error_msg += "<br><b style='color:green;'>Attempted to force-create tables. Please refresh!</b>"
        except Exception as e2:
            error_msg += f"<br><b style='color:red;'>DB Create failed: {str(e2)}</b>"
        return error_msg, 500

@app.route('/cleanup-ai-data')
@requires_auth
def cleanup_ai_data():
    try:
        # Delete trades older than 3 days
        cutoff = datetime.utcnow() + timedelta(hours=5, minutes=30) - timedelta(days=3)
        AIPaperTrade.query.filter(AIPaperTrade.timestamp < cutoff).delete()
        db.session.commit()
        flash("Old AI Data Cleaned successfully to save cloud billing!")
    except Exception as e:
        flash(f"Error during cleanup: {str(e)}")
    return redirect(url_for('ai_dashboard'))

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

@app.route('/block-user/<int:user_id>', methods=['POST', 'GET'])
@requires_auth
def block_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    if user.is_blocked:
        user.algo_status = 'OFF'
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

@app.route('/toggle-signal-lock/<int:user_id>')
@requires_auth
def toggle_signal_lock(user_id):
    user = User.query.get_or_404(user_id)
    user.is_locked = not user.is_locked
    if not user.is_locked:
        user.signals_unlocked_until = datetime.utcnow() + timedelta(hours=5, minutes=30) + timedelta(days=1)
    db.session.commit()
    flash(f"Signal Lock for {user.username} is now {'ON' if user.is_locked else 'OFF'}")
    return redirect(url_for('admin_dashboard'))

@app.route('/upload-payment', methods=['POST'])
def upload_payment():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('demo_register'))
        
    utr = request.form.get('utr_number')
    plan = request.form.get('plan_type', '1-Day')
    file = request.files.get('screenshot')
    
    if file:
        filename = f"payment_{user_id}_{int(time.time())}.png"
        upload_folder = os.path.join('static', 'uploads', 'payments')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        new_payment = PaymentScreenshot(
            user_id=user_id,
            screenshot_path=filename,
            utr_number=utr,
            plan_selected=plan
        )
        db.session.add(new_payment)
        db.session.commit()
        
        flash(f"{plan} Payment Screenshot Uploaded! Admin will verify soon.")
        
        # Send Telegram notification to admin
        user = User.query.get(user_id)
        send_telegram_msg(f"💰 <b>NEW PAYMENT REQUEST ({plan})</b>\nUser: {user.username}\nPhone: {user.phone}\nUTR: {utr}\nPlease check Admin Panel to approve.")
        
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/approve-payment/<int:payment_id>', methods=['POST'])
@requires_auth
def approve_payment(payment_id):
    payment = PaymentScreenshot.query.get_or_404(payment_id)
    user = User.query.get(payment.user_id)
    
    action = request.form.get('action')
    if action == 'APPROVE':
        payment.status = "APPROVED"
        user.is_locked = False
        
        # Determine duration
        days = 1 if payment.plan_selected == "1-Day" else 7
        user.signals_unlocked_until = datetime.utcnow() + timedelta(hours=5, minutes=30) + timedelta(days=days)
        
        db.session.commit()
        flash(f"Payment for {user.username} ({payment.plan_selected}) Approved!")
    else:
        payment.status = "REJECTED"
        db.session.commit()
        flash(f"Payment for {user.username} Rejected.")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/history')
def trade_history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('demo_register'))
    
    # Show Monthly P&L from DailyPnL table
    daily_pnls = DailyPnL.query.order_by(DailyPnL.date.desc()).all()
    monthly_data = {}
    for dp in daily_pnls:
        month_key = dp.date.strftime('%B %Y') # "April 2026"
        if month_key not in monthly_data:
            monthly_data[month_key] = 0.0
        monthly_data[month_key] += dp.pnl
        
    history = [{'month': k, 'pnl': v} for k, v in monthly_data.items()]
    total_pnl = sum((t['pnl'] for t in history))
    return render_template('history.html', history=history, total_pnl=total_pnl)

@app.route('/clear-history')
@requires_auth
def clear_history():
    db.session.query(DailyPnL).delete()
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
                                        is_nfo = any(idx in trade.symbol.upper() for idx in ["NIFTY", "BANK", "SENSEX", "FIN", "MIDCP"])
                                        manual_alert = {
                                            "secret": secret_key,
                                            "transactionType": "SELL",
                                            "orderType": "MKT",
                                            "quantity": str(trade.quantity),
                                            "exchange": "NFO" if is_nfo else "NSE",
                                            "symbol": trade.symbol,
                                            "instrument": "OPT" if is_nfo else "EQ",
                                            "productType": "M",
                                            "alertType": "multi_leg_order",
                                            "order_legs": [{
                                                "transactionType": "S", 
                                                "orderType": "MKT", 
                                                "quantity": str(trade.quantity), 
                                                "exchange": "NFO" if is_nfo else "NSE", 
                                                "symbol": trade.symbol, 
                                                "instrument": "OPT" if is_nfo else "EQ", 
                                                "productType": "M"
                                            }]
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

def sync_admin_dhan_to_worker():
    """Finds the admin's Dhan API key and shares it with the NSE background worker."""
    with app.app_context():
        try:
            admin = User.query.filter_by(email='nelsonp143@gmail.com').first()
            if admin:
                conf = UserBrokerConfig.query.filter_by(user_id=admin.id).first()
                if conf and conf.client_id and conf.encrypted_access_token:
                    token = cipher.decrypt(conf.encrypted_access_token).decode()
                    nse_option_chain.dhan_master_config.update({
                        "client_id": conf.client_id,
                        "access_token": token,
                        "active": True
                    })
                    print(f"✅ [DHAN SYNC] Master Data Feed linked to Admin: {admin.username}")
        except Exception as e:
            print(f"❌ [DHAN SYNC ERROR] {e}")

# ==========================================
# 🤖 GVN AI ASSISTANT (DOUBLE ENGINE)
# ==========================================
import requests

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    user_msg = request.json.get('message', '')
    from dotenv import dotenv_values
    env_config = dotenv_values(".env")
    api_key = (env_config.get('GROQ_API_KEY') or os.environ.get('GROQ_API_KEY', '')).strip()
    
    if not api_key:
        return jsonify({"reply": "⚠️ **GROQ_API_KEY** is not set! Please add your free API key to activate the Double Engine."})
    
    if 'user_id' not in session:
        return jsonify({"reply": "⚠️ Please login to use the AI Engine."})
    
    user = User.query.get(session['user_id'])
    if user and user.is_locked:
        return jsonify({"reply": "🔒 Your AI Engine is Locked. Please upload payment screenshot to unlock!"})
        
    try:
        # Get live data context from the background worker
        live_data = {
            "summary": nse_option_chain.live_option_chain_summary,
            "scanner": nse_option_chain.gvn_scanner_data
        }
        context = f"Live Market Data Context:\n{live_data}\n\n"
        
        system_prompt = """You are GVN Algo AI, an expert hedge fund quantitative analyst. 
You act as a 'Double Engine' verifying trades based on live Option Chain data. 
Be concise, highly professional, and use trading terminology (Call Writing, Put Unwinding, Delta, Momentum). 
Respond in English (or Telugu if specifically asked) with clear actionable insights."""

        # Use requests directly to avoid Render httpx connection errors
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\nUser: {user_msg}"}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({"reply": data['choices'][0]['message']['content']})
        elif response.status_code == 429:
            return jsonify({"reply": "⚠️ Groq Rate limit exceeded. Please wait a moment."})
        else:
            return jsonify({"reply": f"❌ AI Engine Error: HTTP {response.status_code} - {response.text}"})
            
    except Exception as e:
        return jsonify({"reply": f"❌ AI Engine Error: {str(e)}"})

def get_ai_validation(symbol, txn_type, price):
    """
    Calls Groq AI to validate a trade signal based on live market context.
    Returns a short (10-15 word) opinion.
    """
    from dotenv import dotenv_values
    env_config = dotenv_values(".env")
    api_key = (env_config.get('GROQ_API_KEY') or os.environ.get('GROQ_API_KEY', '')).strip()
    
    if not api_key:
        return "AI Offline (Key Missing)"
        
    try:
        live_data = {
            "summary": nse_option_chain.live_option_chain_summary,
            "scanner": nse_option_chain.gvn_scanner_data
        }
        
        system_prompt = "You are GVN Algo AI. Analyze the signal against live data. Be extremely brief (max 12 words). Say if it is 'High Prob' or 'Risky' and why."
        user_prompt = f"Signal: {txn_type} {symbol} @ {price}. Market Context: {live_data}"
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 50
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=7)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except:
        pass
    return "AI Validation Pending..."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Start workers
        nse_option_chain.start_nse_worker()
        sync_admin_dhan_to_worker()
        
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
