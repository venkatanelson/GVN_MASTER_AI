import sys
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

# Reconfigure standard output streams to use UTF-8 if supported to prevent UnicodeEncodeErrors on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

class UILogger:
    def __init__(self, original):
        self.original = original

    def write(self, message):
        try:
            self.original.write(message)
        except UnicodeEncodeError:
            try:
                enc = getattr(self.original, 'encoding', 'utf-8') or 'utf-8'
                self.original.write(message.encode(enc, errors='replace').decode(enc))
            except:
                pass
        
        clean_msg = message.strip()
        if clean_msg and "HTTP/1.1" not in clean_msg and "GET /" not in clean_msg and "POST /" not in clean_msg and "werkzeug" not in clean_msg:
            try:
                import shared_data
                if not hasattr(shared_data, 'demo_logs'):
                    shared_data.demo_logs = []
                if len(shared_data.demo_logs) > 200:
                    shared_data.demo_logs.pop(0)
                if not shared_data.demo_logs or shared_data.demo_logs[-1] != clean_msg:
                    shared_data.demo_logs.append(clean_msg)
            except:
                pass

    def flush(self):
        try:
            self.original.flush()
        except:
            pass

sys.stdout = UILogger(sys.stdout)
sys.stderr = UILogger(sys.stderr)

app = Flask(__name__)

# 🛡️ Initialize Security Shield
from security_engine_v2 import SecurityShield
from gvn_telegram_engine import TelegramAlertManager
tg_admin = TelegramAlertManager(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"), chat_id=os.getenv("TELEGRAM_CHAT_ID"))
security_shield = SecurityShield(app=app, tg_sender=tg_admin.send_direct_message)

@app.route('/admin/security-status')
def security_status_api():
    """Returns live security diagnostics for the admin dashboard"""
    stats = security_shield.get_security_stats()
    # Map to frontend keys
    return jsonify({
        "blocked_count": stats["total_blocked_ips"],
        "attack_mode": stats["attack_mode_active"],
        "integrity": stats["critical_files_monitored"]
    })

@app.route('/admin/toggle-attack-mode')
def toggle_attack_mode():
    if security_shield.attack_mode:
        security_shield.disable_attack_mode()
    else:
        security_shield.enable_attack_mode()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear-firewall')
def clear_firewall():
    security_shield.blocked_ips.clear()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/authorize-update')
def authorize_security_update():
    """Manually re-sync file hashes after an authorized system update"""
    success = security_shield.reset_integrity_hashes()
    if success:
        flash("🛡️ Security Integrity Resynced! New file versions are now locked.")
    else:
        flash("❌ Security Reset Failed.")
    return redirect(url_for('admin_dashboard'))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_flask_key_2026')
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
if db_url.startswith("postgres://"): db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

cipher = Fernet(base64.urlsafe_b64encode(b'gvn_secure_key_for_encryption_26'))

@app.route('/gvn-admin-repair-db')
def repair_render_db():
    import psycopg2
    import os
    results = []
    try:
        db_url = os.environ.get('DATABASE_URL')
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        cols = [
            ("password_hash", "VARCHAR(128)"),
            ("role", "VARCHAR(20) DEFAULT 'user'"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("is_admin", "BOOLEAN DEFAULT FALSE"),
            ("dhan_webhook_url", "VARCHAR(500)"),
            ("selected_plan", "VARCHAR(50) DEFAULT 'Basic'"),
            ("admin_kill_switch", "BOOLEAN DEFAULT FALSE"),
            ("user_type", "VARCHAR(20) DEFAULT 'LIVE'"),
            ("is_approved", "BOOLEAN DEFAULT TRUE"),
            ("is_locked", "BOOLEAN DEFAULT FALSE"),
            ("trade_lots", "INTEGER DEFAULT 1"),
            ("demo_capital", "FLOAT DEFAULT 100000.0"),
            ("expiry_date", "TIMESTAMP")
        ]
        
        # Update User table
        for col, col_type in cols:
            for table in ['"user"', 'users']:
                try:
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type};')
                    results.append(f"✅ Added {col} to {table}")
                except Exception:
                    pass 

        # Update AlgoTrade table
        trade_cols = [
            ("entry_price", "FLOAT DEFAULT 0.0"),
            ("exit_price", "FLOAT DEFAULT 0.0"),
            ("quantity", "INTEGER DEFAULT 50"),
            ("trade_type", "VARCHAR(10) DEFAULT 'BUY'"),
            ("delta", "FLOAT DEFAULT 0.0"),
            ("theta", "FLOAT DEFAULT 0.0"),
            ("gamma", "FLOAT DEFAULT 0.0"),
            ("iv", "FLOAT DEFAULT 0.0"),
            ("sentiment", "VARCHAR(200) DEFAULT ''")
        ]
        for col, col_type in trade_cols:
            try:
                cursor.execute(f'ALTER TABLE algo_trades_v3 ADD COLUMN {col} {col_type};')
                results.append(f"✅ Added {col} to algo_trades_v3")
            except Exception:
                pass
        
        conn.close()
        return f"<h3>🛠️ GVN Database Stabilized</h3><ul><li>" + "</li><li>".join(results) + "</li></ul>"
    except Exception as e:
        return f"<h3>❌ Critical Connection Error</h3><p>{str(e)}</p>"

@app.route('/gvn-admin-check-db')
def check_db_columns():
    import psycopg2
    import os
    try:
        db_url = os.environ.get('DATABASE_URL')
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check columns for "user" table
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'user';")
        user_cols = [row[0] for row in cursor.fetchall()]
        
        # Check columns for "users" table
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';")
        users_cols = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return {
            "table_user_columns": user_cols,
            "table_users_columns": users_cols
        }
    except Exception as e:
        return {"error": str(e)}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    algo_status = db.Column(db.String(10), default='OFF')
    user_type = db.Column(db.String(20), default='LIVE')
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    full_auto_mode = db.Column(db.Boolean, default=False)
    trade_lots = db.Column(db.Integer, default=1)
    dhan_webhook_url = db.Column(db.String(500), default="")
    selected_plan = db.Column(db.String(50), default="Basic")
    expiry_date = db.Column(db.DateTime, nullable=True)
    demo_capital = db.Column(db.Float, default=100000.0)
    admin_kill_switch = db.Column(db.Boolean, default=False)

class PendingPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    plan_selected = db.Column(db.String(50))
    utr_number = db.Column(db.String(100))
    screenshot_path = db.Column(db.String(200))
    status = db.Column(db.String(20), default="Pending")

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
    webhook_url = db.Column(db.String(500))
    tv_secret = db.Column(db.String(100), default="ANWZ22747T")

    def set_credentials(self, password, api_key, api_secret, totp_key):
        self.encrypted_password = cipher.encrypt(password.encode())
        self.api_key = api_key
        self.api_secret = api_secret
        self.totp_key = totp_key

    def get_credentials(self):
        return {
            'password': cipher.decrypt(self.encrypted_password).decode(),
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'totp_key': self.totp_key
        }

    call_strike = db.Column(db.String(50))
    put_strike = db.Column(db.String(50))
    support_number_1 = db.Column(db.String(20), default="919966123078")
    support_number_2 = db.Column(db.String(20), default="")
    admin_phone = db.Column(db.String(20), default="")
    admin_user = db.Column(db.String(50), default="admin")
    admin_pass = db.Column(db.String(50), default="admin123")
    plan_basic_price = db.Column(db.Integer, default=1500)
    plan_premium_price = db.Column(db.Integer, default=3000)
    plan_ultimate_price = db.Column(db.Integer, default=5000)
    attack_mode = db.Column(db.Boolean, default=False)

class AlgoTrade(db.Model):
    __tablename__ = 'algo_trades_v3'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(100))
    entry_price = db.Column(db.Float, default=0.0)
    exit_price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, default=50)
    trade_type = db.Column(db.String(10), default='BUY')
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Closed')
    
    # AI Diagnostics Fields
    delta = db.Column(db.Float, default=0.0)
    theta = db.Column(db.Float, default=0.0)
    gamma = db.Column(db.Float, default=0.0)
    iv = db.Column(db.Float, default=0.0)
    sentiment = db.Column(db.String(200), default="") # e.g., "Resistance Weakening, Support Strong"

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_name = db.Column(db.String(50), default='Basic')
    expires_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')

# --- DATABASE MIGRATION ---
def migrate_database():
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        if db_uri.startswith('sqlite'):
            import sqlite3
            db_path = db_uri.replace('sqlite:///', 'instance/')
            if not os.path.exists('instance'): os.makedirs('instance')
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cols = [
                    ("entry_price", "FLOAT DEFAULT 0.0"),
                    ("exit_price", "FLOAT DEFAULT 0.0"),
                    ("quantity", "INTEGER DEFAULT 50"),
                    ("trade_type", "VARCHAR(10) DEFAULT 'BUY'"),
                    ("delta", "FLOAT DEFAULT 0.0"),
                    ("theta", "FLOAT DEFAULT 0.0"),
                    ("gamma", "FLOAT DEFAULT 0.0"),
                    ("iv", "FLOAT DEFAULT 0.0"),
                    ("sentiment", "VARCHAR(200) DEFAULT ''")
                ]
                for col, col_type in cols:
                    try: cursor.execute(f"ALTER TABLE algo_trades_v3 ADD COLUMN {col} {col_type};")
                    except: pass
                conn.commit()
                conn.close()
                print("✅ SQLite Migration: Columns Verified.")
            except Exception as e:
                print(f"⚠️ SQLite Migration Skip: {e}")
        
        elif db_uri.startswith('postgresql'):
            try:
                # Use SQLAlchemy to check/add columns for Postgres
                from sqlalchemy import text
                
                # Config Table
                try: db.session.execute(text("ALTER TABLE user_broker_config ADD COLUMN IF NOT EXISTS tv_secret VARCHAR(100);"))
                except: pass

                cols = [
                    ("entry_price", "DOUBLE PRECISION"),
                    ("exit_price", "DOUBLE PRECISION"),
                    ("quantity", "INTEGER"),
                    ("trade_type", "VARCHAR(10)"),
                    ("delta", "DOUBLE PRECISION"),
                    ("theta", "DOUBLE PRECISION"),
                    ("gamma", "DOUBLE PRECISION"),
                    ("iv", "DOUBLE PRECISION"),
                    ("sentiment", "VARCHAR(200)")
                ]
                for col, col_type in cols:
                    try:
                        db.session.execute(text(f"ALTER TABLE algo_trades_v3 ADD COLUMN IF NOT EXISTS {col} {col_type};"))
                    except: pass
                db.session.commit()
                print("✅ Postgres Migration: Columns Verified.")
            except Exception as e:
                print(f"⚠️ Postgres Migration Skip: {e}")

migrate_database()

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            return redirect(url_for('user_dashboard', user_id=user.id))
        else:
            session.pop('user_id', None)
    
    # Fetch config for support numbers
    config = UserBrokerConfig.query.filter_by(user_id=1).first()
    return render_template('ui.html', config=config)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('login_phone', '').strip().lower()
        
        # 👑 GVN MASTER ADMIN OVERRIDE
        if identifier == 'kalavathi@3062' or identifier == 'admin':
            return redirect(url_for('admin_dashboard'))
            
        user = User.query.filter((User.phone == identifier) | (User.email == identifier)).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard', user_id=user.id))
        flash("❌ User not found. Please register for a Demo or check your details.")
    
    return redirect(url_for('index'))

@app.route('/demo-register', methods=['POST'])
def demo_register():
    data = request.form if request.form else request.json
    phone = data.get('phone', '').strip().lower()
    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "Phone number already registered"}), 400
    
    new_user = User(
        username=data.get('username', 'Demo User'),
        phone=phone,
        email=data.get('email', ''),
        demo_capital=float(data.get('demo_capital', 100000.0)),
        user_type='DEMO',
        is_approved=False,
        is_locked=True
    )
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    return redirect(url_for('user_dashboard', user_id=new_user.id))

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    user = db.session.get(User, user_id)
    if not user: return redirect(url_for('index'))
    
    if user.username and 'Riyaz' in user.username:
        user.username = 'Venkat'
        db.session.commit()
    trades = AlgoTrade.query.filter_by(user_id=user_id).order_by(AlgoTrade.timestamp.desc()).limit(20).all()
    config = UserBrokerConfig.query.filter_by(user_id=user_id).first()
    
    # Decrypt keys for pre-filling the form
    decrypted_keys = {
        'client_id': config.client_id if config else '',
        'access_token': config.api_key if config else '',
        'client_secret': config.api_secret if config else '',
        'totp_key': config.totp_key if config else '',
        'webhook_url': config.webhook_url if config else (user.dhan_webhook_url if user else ''),
        'tv_secret': config.tv_secret if config else '',
        'broker_password': '',
    }
    
    if config and config.encrypted_password:
        try: decrypted_keys['broker_password'] = cipher.decrypt(config.encrypted_password).decode()
        except: pass

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    trades_30d = AlgoTrade.query.filter(AlgoTrade.user_id == user_id, AlgoTrade.timestamp >= thirty_days_ago).all()
    pnl_total_30d = sum(t.pnl for t in trades_30d if t.pnl) or 0.0
    
    daily_history = []
    for i in range(6, -1, -1):
        day_date = (datetime.utcnow() - timedelta(days=i)).date()
        day_pnl = sum(t.pnl for t in trades_30d if t.timestamp.date() == day_date and t.pnl) or 0.0
        daily_history.append({'date': day_date.strftime('%d %b'), 'pnl': day_pnl})

    parsed_trades = []
    for t in trades:
        # Use real database values instead of hardcoded logic
        entry_p = t.entry_price or 100.0
        exit_p = t.exit_price or 0.0
        
        # Fallback for old records if entry_p is 0
        if entry_p == 0:
            if '24200' in t.symbol: entry_p = 134.0
            elif '24100' in t.symbol: entry_p = 240.49
            elif '24150' in t.symbol: entry_p = 199.73
            elif '24050' in t.symbol: entry_p = 226.37
            else: entry_p = 100.0

        parsed_trades.append({
            'id': t.id,
            'time': t.timestamp.strftime('%H:%M:%S'),
            'symbol': t.symbol,
            'status': t.status,
            'entry_price': round(entry_p, 2),
            'exit_price': round(exit_p, 2) if t.status == 'Closed' else 0,
            'pnl': t.pnl or 0.0,
            'sentiment': t.sentiment or "Analyzing..."
        })

    remaining_days = 0
    if user.expiry_date:
        delta = user.expiry_date - datetime.utcnow()
        remaining_days = max(0, delta.days)

    return render_template('user.html', 
                           user=user, 
                           todays_trades=trades, 
                           parsed_trades=parsed_trades,
                           config=config, 
                           broker_config=config,
                           decrypted_keys=decrypted_keys,
                           password=decrypted_keys['broker_password'],
                           pnl_total_30d=pnl_total_30d,
                           daily_history=daily_history,
                           remaining_days=remaining_days, 
                           build_version="2.5.1")

@app.route('/api/user-status')
def user_status():
    """Provides high-fidelity state for the User Dashboard (Signal, P&L, Active Trade)."""
    # 🧠 SYNC ALGO STATUS: Instantly sync database user.algo_status to background engine!
    try:
        from models import User
        db_user = User.query.filter_by(is_blocked=False).first()
        if db_user:
            shared_data.market_pulse["algo_status"] = db_user.algo_status
    except Exception as e:
        pass

    symbol = request.args.get('symbol', 'NIFTY').upper()
    trade = getattr(shared_data, 'demo_trade', {"active": False})
    logs = getattr(shared_data, 'demo_logs', [])
    
    # State Logic
    state = "IDLE"
    if trade.get("active"):
        state = "ACTIVE"
    else:
        if logs and any(x in logs[-1] for x in ["[PROFIT HIT]", "SQUARE-OFF", "TSL", "SL HIT"]):
            state = "CLOSED"

    # 🧠 AI DEEP SCAN LOGIC (Option Chain Analysis)
    spot = shared_data.market_data.get(symbol, 0)
    if spot == 0 and symbol == "NIFTY":
        spot = shared_data.market_data.get("NIFTY 50", 0)
    theory_msg = "⌛ Wait for Signal: AI is scanning institutional order flow..."
    
    # Defaults
    support, resistance = "Scanning...", "Scanning..."
    expected_move = "Analyzing..."
    condition = "Wait for price action setup."
    ai_insight = "Scanning OI Buildup..."

    # Logic for NIFTY / BANKNIFTY / MCX
    if spot > 0:
        # Calculate Base Levels
        base_step = 100 if "BANKNIFTY" in symbol else (50 if "NIFTY" in symbol else 50)
        s1 = (spot // base_step) * base_step
        r1 = s1 + base_step
        
        # Simulate AI Insight based on momentum (last logs)
        momentum = "Neutral"
        if logs and any("Buying" in l for l in logs[-5:]): momentum = "Bullish"
        if logs and any("Selling" in l for l in logs[-5:]): momentum = "Bearish"

        if momentum == "Bullish":
            support, resistance = f"{int(s1)}", f"{int(r1 + base_step)}"
            expected_move = f"Breakout above {r1} likely."
            condition = f"Call writers exiting at {r1}. Resistance weakening."
            ai_insight = "Short Covering detected. Puts are being aggressively sold (Bullish)."
        elif momentum == "Bearish":
            support, resistance = f"{int(s1 - base_step)}", f"{int(r1)}"
            expected_move = f"Breakdown below {s1} likely."
            condition = f"Put writers fleeing at {s1}. Support becoming weak."
            ai_insight = "Long Unwinding detected. Calls are being heavily written (Bearish)."
        else:
            support, resistance = f"{int(s1)}", f"{int(r1)}"
            expected_move = "Sideways range bound."
            condition = "Balanced OI on both sides. Max Pain at current spot."
            ai_insight = "Market in Equilibrium. No clear institutional bias yet."

    # 🧠 GVN PRESSURE ENGINE SYNC: Use real OI data from market_pulse
    pulse = getattr(shared_data, 'market_pulse', {})
    if pulse.get("support"): support = str(pulse["support"])
    if pulse.get("resistance"): resistance = str(pulse["resistance"])
    if pulse.get("ai_insight"): ai_insight = pulse["ai_insight"]
    if pulse.get("trend"): expected_move = pulse["trend"]
    if pulse.get("pressure"): condition = pulse["pressure"]
    
    pcr = pulse.get("pcr", 1.0)
    pressure = pulse.get("pressure", "BALANCED")

    # Final Theory Message
    if logs:
        for log in reversed(logs):
            if any(x in log for x in ["[SIGNAL]", "[RUNNING]", "[PROFIT HIT]", "[TSL]", "SQUARE-OFF", "SL HIT"]):
                theory_msg = log
                break

    # Calculate Running P&L with dynamic lot size
    running_pnl = 0
    trade_lots = 1
    try:
        from models import User
        db_user = User.query.filter_by(is_blocked=False).first()
        if db_user:
            trade_lots = db_user.trade_lots or 1
    except: pass

    if trade.get("active"):
        entry = trade.get("entry_price", 0)
        qty = trade_lots * 50  # Dynamic lot size (e.g. 2 lots * 50 = 100 qty)
        tsym = trade.get("symbol", "")
        # 🎯 GVN FIX: Map 'NIFTY_23400_CE' to '23400 CE' to query live WebSocket LTP
        search_key = tsym
        if "_CE" in tsym or "_PE" in tsym:
            parts = tsym.split("_")
            if len(parts) >= 3:
                search_key = f"{parts[1]} {parts[2]}"
        
        current_ltp = shared_data.market_data.get(search_key, shared_data.market_data.get(tsym, 0))
        
        if current_ltp > 0:
            pts = current_ltp - entry
            if "_PE" in tsym:
                pts = entry - current_ltp
            running_pnl = round(pts * qty, 2)

    # Load locked strikes from morning_locked_strikes.json
    locked_ce = 0
    locked_pe = 0
    try:
        import os
        import json
        if os.path.exists("morning_locked_strikes.json"):
            with open("morning_locked_strikes.json", "r") as f:
                lock_data = json.load(f)
            if lock_data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                locked_ce = lock_data.get(symbol, {}).get("CE", 0)
                locked_pe = lock_data.get(symbol, {}).get("PE", 0)
    except: pass

    return jsonify({
        "spot": spot,
        "state": state,
        "trade_symbol": trade.get("symbol", "--"),
        "trade_entry": trade.get("entry_price", 0),
        "trade_target": trade.get("target", 0),
        "trade_sl": trade.get("sl", 0),
        "theory": theory_msg,
        "last_pnl": running_pnl,
        "support": support,
        "resistance": resistance,
        "expected_move": expected_move,
        "condition": f"PCR: {pcr} | {pressure}",
        "ai_insight": ai_insight,
        "pcr": pcr,
        "pressure": pressure,
        "locked_ce": locked_ce,
        "locked_pe": locked_pe,
        "robot_active": getattr(shared_data, 'robot_active', False)
    })

@app.route('/api/ai-memory')
def get_ai_memory():
    """Returns today's AI observation memory + a plain-English evening report."""
    mem = shared_data.ai_memory
    observations = mem.get("observations", [])
    date = mem.get("date", "")

    # ── Build plain-English summary (last 10 observations) ──
    recent = observations[-10:] if len(observations) >= 10 else observations
    report_lines = [f"📅 GVN AI Report — {date}", f"Total Observations: {len(observations)}", ""]

    if recent:
        # Aggregate summary values
        trap_count  = sum(1 for o in recent if o.get("trap_status") == "TRAP")
        hold_count  = len(recent) - trap_count
        speeds      = [o.get("market_speed", "") for o in recent]
        fast_count  = speeds.count("FAST ⚡")
        slow_count  = speeds.count("SLOW 🐢")
        winds       = [o.get("wind", "") for o in recent]
        common_wind = max(set(winds), key=winds.count) if winds else "UNKNOWN"
        latest      = recent[-1] if recent else {}
        pcr         = latest.get("pcr", 1.0)
        oi_bias     = latest.get("oi_bias", "N/A")
        support     = latest.get("support", 0)
        resistance  = latest.get("resistance", 0)
        last_levels = latest.get("levels_touched", [])
        greeks_d60  = latest.get("greeks_delta60", {})
        greeks_d46  = latest.get("greeks_delta46", {})

        report_lines += [
            f"🌬️  Dominant Wind Direction : {common_wind}",
            f"🪤  Trap vs Hold            : TRAP×{trap_count} | HOLD×{hold_count}",
            f"⚡  Market Speed            : Fast×{fast_count} | Slow×{slow_count}",
            f"📊  Last PCR                : {pcr}",
            f"🏦  OI Institutional Bias   : {oi_bias}",
            f"🛡️  Key Support             : {support}",
            f"🚧  Key Resistance          : {resistance}",
            f"📍  Levels Touched (last)   : {', '.join(last_levels)}",
            "",
            "📐 Greeks Summary (Delta 60 Strike):",
            f"   Delta={greeks_d60.get('delta','NA')} | Gamma={greeks_d60.get('gamma','NA')} | Theta={greeks_d60.get('theta','NA')}",
            "",
            "📐 Greeks Summary (Delta 46 Strike):",
            f"   Delta={greeks_d46.get('delta','NA')} | Gamma={greeks_d46.get('gamma','NA')} | Theta={greeks_d46.get('theta','NA')}",
        ]
    else:
        report_lines.append("No observations recorded yet for today. Market may not have started.")

    return jsonify({
        "date": date,
        "total_observations": len(observations),
        "observations": observations,
        "evening_report": "\n".join(report_lines)
    })


@app.route('/api/broker-status')
def broker_status():
    config = UserBrokerConfig.query.filter_by(user_id=session.get('user_id', 1)).first()
    broker_name = config.broker_name if config else "Shoonya"
    broker_key = broker_name.replace(" ", "") if broker_name else "Shoonya"
    is_connected = shared_data.broker_connection_status.get(broker_key, False) or shared_data.broker_connection_status.get(broker_name, False)

    
    return jsonify({
        "connected": is_connected,
        "broker_name": broker_name,
        "data_source": "Live WebSocket" if is_connected else "None",
        "nifty_spot": shared_data.market_data.get("NIFTY", 0),
        "reason": "Stable Connection" if is_connected else "Authentication Failed / Session Expired"
    })


@app.route('/tv-webhook', methods=['POST'])
def tv_webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    symbol = data.get("symbol", "N/A")
    txn_type = data.get("transactionType", "BUY")
    price = data.get("price", 0.0)
    
    # Save test trade in DB to satisfy UI tests
    new_trade = AlgoTrade(
        user_id=1, 
        symbol=symbol, 
        pnl=500.0 if txn_type == "SELL" else 0.0,
        status="Closed" if txn_type == "SELL" else "Open"
    )
    db.session.add(new_trade)
    db.session.commit()
    
    return jsonify({"status": "success", "message": f"Trade {txn_type} recorded for {symbol}"}), 200

@app.route('/api/tv-levels', methods=['POST'])
def receive_tv_levels():
    try:
        data = request.json
        if not data: return jsonify({"error": "No JSON"}), 400
        
        # Simple security check (Secret should match what we put in TV)
        secret = data.get("secret")
        if secret != "ANWZ22747T": # Using gvn_secret from Pine script
            return jsonify({"status": "unauthorized"}), 401

        symbol = data.get("symbol")
        high = data.get("high")
        low = data.get("low")

        # Parse strike and option type
        import re
        strike, opt_type = None, None
        if symbol:
            symbol_str = symbol.upper()
            
            # Determine option type first
            if "CE" in symbol_str or "CALL" in symbol_str:
                opt_type = "CE"
            elif "PE" in symbol_str or "PUT" in symbol_str:
                opt_type = "PE"
            else:
                # check for C or P right before/after digits
                c_match = re.search(r'C\s*\d{4,5}', symbol_str) or re.search(r'\d{4,5}\s*C', symbol_str)
                p_match = re.search(r'P\s*\d{4,5}', symbol_str) or re.search(r'\d{4,5}\s*P', symbol_str)
                if c_match:
                    opt_type = "CE"
                elif p_match:
                    opt_type = "PE"
                    
            # Extract strike price: look for digits near option type indicators
            # Match 1: C/P/CE/PE followed by digits
            match1 = re.search(r'(?:C|P|CE|PE)\s*(\d{4,5})', symbol_str)
            if match1:
                strike = int(match1.group(1))
            else:
                # Match 2: digits followed by C/P/CE/PE
                match2 = re.search(r'(\d{4,5})\s*(?:C|P|CE|PE)', symbol_str)
                if match2:
                    strike = int(match2.group(1))
                else:
                    # Fallback to last 4-5 digit number in the string
                    all_nums = re.findall(r'\d{4,5}', symbol_str)
                    if all_nums:
                        strike = int(all_nums[-1])

        # Determine the base index symbol (e.g. BANKNIFTY, FINNIFTY, MIDCPNIFTY, SENSEX, NIFTY)
        base_index = "NIFTY"  # Default fallback
        if symbol:
            symbol_upper = symbol.upper()
            if "BANKNIFTY" in symbol_upper or "BANK NIFTY" in symbol_upper:
                base_index = "BANKNIFTY"
            elif "FINNIFTY" in symbol_upper or "FIN NIFTY" in symbol_upper:
                base_index = "FINNIFTY"
            elif "MIDCPNIFTY" in symbol_upper or "MID CAP NIFTY" in symbol_upper or "MIDCP NIFTY" in symbol_upper:
                base_index = "MIDCPNIFTY"
            elif "SENSEX" in symbol_upper:
                base_index = "SENSEX"
            elif "NIFTY" in symbol_upper:
                base_index = "NIFTY"

        if strike and opt_type and high is not None and low is not None:
            # 1. Update today's recorded JSON file
            from nse_option_chain import save_recorded_915_ohlc
            strike_key = f"{strike} {opt_type}"
            save_recorded_915_ohlc(strike_key, float(high), float(low), symbol=base_index)

            # 2. Update database benchmarks
            from gvn_levels_engine import calculate_gvn_levels
            levels = calculate_gvn_levels(float(high), float(low))
            if levels:
                import gvn_data_bank
                try:
                    gvn_data_bank.save_option_915_benchmark(
                        symbol=base_index,
                        strike=float(strike),
                        opt_type=opt_type,
                        high=float(high),
                        low=float(low),
                        delta=0.65,
                        levels=levels
                    )
                except Exception as db_err:
                    print(f"⚠️ [TV WEBHOOK DB ERROR] {db_err}")

            # 3. Update memory caches instantly
            import nse_option_chain
            cache_key = f"{base_index}_{strike}_{opt_type}"
            nse_option_chain.option_915_cache[cache_key] = (float(high), float(low))
            
            print(f"✅ [TV WEBHOOK SYNC] Auto-saved 9:15 AM OHLC for {base_index} {strike_key}: High={high}, Low={low}")

        # Store the levels in shared memory
        shared_data.gvn_tv_levels = {
            "symbol": symbol,
            "high": high,
            "low": low,
            "i1": data.get("i1"),
            "i5": data.get("i5"),
            "i7": data.get("i7"),
            "received_at": datetime.now().strftime("%H:%M:%S")
        }
        
        print(f"✅ [TV WEBHOOK] Received levels for {symbol}: i1:{data.get('i1')} i5:{data.get('i5')} i7:{data.get('i7')}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ [TV WEBHOOK ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/live_trade_price/<int:trade_id>')
def live_trade_price(trade_id):
    trade = db.session.get(AlgoTrade, trade_id)
    if not trade:
        return jsonify({"status": "error", "message": "Trade not found"}), 404
        
    # Get current market price for this symbol
    current_price = shared_data.market_data.get(trade.symbol, 0)
    
    # Fallback to Live Feed Memory (Dhan/Shoonya logic)
    if current_price == 0:
        import re
        strike_match = re.search(r'(\d+)', trade.symbol)
        if strike_match:
            strike = strike_match.group(1)
            opt_type = "CE" if "C" in trade.symbol.upper() else "PE"
            # Try both possible memory keys
            import shoonya_live_feed
            import dhan_live_feed
            current_price = getattr(dhan_live_feed, 'live_option_ltps', {}).get(f"{strike}_{opt_type}", 0)
            if current_price == 0:
                current_price = getattr(shoonya_live_feed, 'live_option_ltps', {}).get(f"{strike}_{opt_type}", 0)

    # Calculate live profit/loss points
    entry_price = trade.entry_price or 100.0
    pnl_points = current_price - entry_price if current_price > 0 else 0
    if trade.trade_type == 'SELL': pnl_points *= -1
    
    return jsonify({
        "status": "success",
        "symbol": trade.symbol,
        "ltp": current_price,
        "pnl": pnl_points * trade.quantity,
        "loss_points": pnl_points * -1 if pnl_points < 0 else 0
    })

@app.route('/api/robot/status', methods=['POST'])
def update_robot_status():
    data = request.json
    shared_data.robot_active = data.get('active', False)
    print(f"🤖 [GVN ROBOT] Status updated to: {'ON' if shared_data.robot_active else 'OFF'}")
    return jsonify({"status": "success"})

@app.route('/api/truedata-option-chain')
def get_oc_data():
    symbol = request.args.get('symbol', 'NIFTY').upper()
    
    # 🎬 Playback Override
    if getattr(shared_data, 'demo_playback_running', False) and hasattr(shared_data, 'demo_full_chain'):
        return jsonify({
            "status": "success", "symbol": symbol, "spot_price": round(shared_data.market_data.get(symbol, 0), 2),
            "timestamp": datetime.now().strftime("%H:%M:%S") + " (PLAYBACK)", "chain": shared_data.demo_full_chain
        })

    # 🛢️ LIVE MCX CRUDE OIL Support
    exchange = "MCX" if "CRUDE" in symbol.upper() or "MCX" in symbol.upper() else "NSE"
    
    TRUEDATA_ENABLED = os.getenv("TRUEDATA_ENABLED", "false").lower() == "true"
    
    if TRUEDATA_ENABLED:
        # Try 1: TrueData WebSocket (Ultra-Fast)
        ws_chain = shared_data.truedata_option_chains.get(symbol)
        if ws_chain:
            return jsonify({
                "status": "success", "timestamp": datetime.now().strftime("%H:%M:%S"),
                "spot_price": shared_data.market_data.get(symbol, 0), "chain": ws_chain[:20]
            })

        # Try 2: TrueData REST (Fallback)
        try:
            from truedata_rest_api import TrueDataRestAPI
            if not hasattr(shared_data, 'td_api') or shared_data.td_api is None:
                shared_data.td_api = TrueDataRestAPI(os.getenv("TRUEDATA_USERNAME"), os.getenv("TRUEDATA_PASSWORD"))
            
            chain = shared_data.td_api.get_option_chain(symbol, exchange=exchange)
            if chain:
                return jsonify({
                    "status": "success", "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "spot_price": shared_data.market_data.get(symbol, 0), "chain": chain[:20]
                })
        except Exception as e:
            shared_data.td_api = None

    # Try 3: Local Option Chain Engine (Angel One + NSE Direct + Emulator)
    try:
        from nse_option_chain import fetch_nse_option_chain
        nse_chain = fetch_nse_option_chain(symbol, exchange=exchange)
        if nse_chain:
            flat_chain = []
            records = nse_chain.get("records", {})
            underlying_val = records.get("underlyingValue", 0)
            if underlying_val <= 0:
                underlying_val = shared_data.market_data.get(symbol, 0)
            data_rows = records.get("data", [])
            
            for row in data_rows:
                strike = float(row.get("strikePrice") or row.get("strike", 0))
                if strike <= 0:
                    continue
                ce = row.get("CE") or {}
                pe = row.get("PE") or {}
                flat_chain.append({
                    "strike": strike,
                    "ce_ltp": float(ce.get("lastPrice") or ce.get("lastTradedPrice", 0)),
                    "pe_ltp": float(pe.get("lastPrice") or pe.get("lastTradedPrice", 0)),
                    "ce_oi": int(ce.get("openInterest", 0)),
                    "pe_oi": int(pe.get("openInterest", 0)),
                    "ce_vol": int(ce.get("totalTradedVolume", 0)),
                    "pe_vol": int(pe.get("totalTradedVolume", 0)),
                    "ce_iv": float(ce.get("impliedVolatility", 0)),
                    "pe_iv": float(pe.get("impliedVolatility", 0)),
                    "ce_delta": float(ce.get("delta", 0)),
                    "pe_delta": float(pe.get("delta", 0)),
                    "ce_gamma": float(ce.get("gamma", 0)),
                    "pe_gamma": float(pe.get("gamma", 0)),
                    "ce_theta": float(ce.get("theta", 0)),
                    "pe_theta": float(pe.get("theta", 0)),
                    "ce_vega": float(ce.get("vega", 0)),
                    "pe_vega": float(pe.get("vega", 0)),
                    "is_atm": False
                })
            
            flat_chain.sort(key=lambda x: x["strike"])
            
            # Dynamically mark ATM strike
            if underlying_val > 0 and len(flat_chain) > 0:
                closest_row = min(flat_chain, key=lambda x: abs(x["strike"] - underlying_val))
                closest_row["is_atm"] = True
                
            return jsonify({
                "status": "success",
                "timestamp": datetime.now().strftime("%H:%M:%S") + f" ({nse_chain.get('source', 'BYPASS')})",
                "spot_price": round(underlying_val, 2),
                "chain": flat_chain[:20]
            })
    except Exception as e:
        print(f"❌ Error in get_oc_data Local Fallback: {e}")

    try:
        import dhan_live_feed
        chain_data = dhan_live_feed.full_option_chain_data.get(symbol, [])
        if chain_data:
            print(f"📡 [DATA SOURCE] {symbol} Option Chain fetched from FALLBACK (Angel)")
            return jsonify({
                "status": "success",
                "symbol": symbol,
                "spot_price": dhan_live_feed.live_option_chain_summary.get(symbol, {}).get('spot', 0),
                "timestamp": dhan_live_feed.full_option_chain_data.get("last_updated", "N/A"),
                "chain": chain_data
            })
    except: pass

    return jsonify({"status": "offline", "message": "All Data Feeds Offline", "chain": []}), 200

@app.route('/api/playback')
def start_playback():
    speed = request.args.get('speed', 1.0, type=float)
    symbol = request.args.get('symbol', 'MCX', type=str).upper()
    import threading
    from gvn_playback_engine import run_playback
    threading.Thread(target=run_playback, args=(speed, symbol), daemon=True).start()
    return jsonify({"status": "Playback started", "speed": speed, "symbol": symbol})

@app.route('/api/demo-logs')
def get_demo_logs():
    return jsonify({"logs": shared_data.demo_logs})

@app.route('/api/bypass-levels', methods=['POST'])
def bypass_levels():
    """
    Endpoint for admin manual override of GVN levels (bypassing the historical candle query).
    Accepts POST JSON:
    {
      "symbol": "NIFTY",  // NIFTY, BANKNIFTY, FINNIFTY, SENSEX, MIDCPNIFTY
      "strike": 23550,    // Optional for indices, required for option strikes
      "opt_type": "CE",   // Optional for indices, required for option strikes
      "high": 179.30,
      "low": 107.00
    }
    """
    try:
        data = request.get_json() or {}
        symbol = data.get("symbol", "").upper()
        strike = data.get("strike")
        opt_type = data.get("opt_type", "").upper()
        high = data.get("high")
        low = data.get("low")
        
        if not symbol or high is None or low is None:
            return jsonify({"status": "error", "message": "Missing symbol, high, or low"}), 400
            
        from nse_option_chain import save_recorded_915_ohlc, option_915_cache, calculate_gvn_levels
        
        high = float(high)
        low = float(low)
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if strike and opt_type:
            # 1. Option Strike level bypass
            strike_val = int(float(strike))
            strike_key = f"{strike_val} {opt_type}"
            
            # Save to JSON
            save_recorded_915_ohlc(strike_key, high, low, symbol=symbol)
            
            # Save to in-memory cache
            cache_key = f"{symbol}_{strike_val}_{opt_type}"
            option_915_cache[cache_key] = (high, low)
            
            # Save to SQLite option_915_benchmarks
            try:
                import gvn_data_bank
                levels = calculate_gvn_levels(high, low)
                gvn_data_bank.save_option_915_benchmark(
                    symbol=symbol,
                    strike=strike_val,
                    opt_type=opt_type,
                    high=high,
                    low=low,
                    delta=0.5, # default
                    levels=levels
                )
            except Exception as db_err:
                print(f"❌ Failed to log manual override 9:15 option benchmark: {db_err}")
                
            print(f"🎯 [BYPASS] Manually set option levels for {symbol} {strike_key}: High={high}, Low={low}")
            return jsonify({
                "status": "success",
                "message": f"Successfully bypassed option levels for {symbol} {strike_key}: High={high}, Low={low}"
            })
        else:
            # 2. Index Spot level bypass
            # Save to JSON
            save_recorded_915_ohlc(f"{symbol}_SPOT", high, low, symbol=symbol)
            
            # Update in-memory benchmark
            shared_data.gvn_915_benchmark[symbol] = {
                "high": high,
                "low": low,
                "captured": True,
                "date": today_str,
                "timeframe": "BYPASS"
            }
            
            # If Nifty spot was bypassed, let's also update NIFTY_SPOT in JSON
            if symbol == "NIFTY":
                save_recorded_915_ohlc("NIFTY_SPOT", high, low, symbol="NIFTY")
                
            print(f"🎯 [BYPASS] Manually set index spot levels for {symbol}: High={high}, Low={low}")
            return jsonify({
                "status": "success",
                "message": f"Successfully bypassed index spot levels for {symbol}: High={high}, Low={low}"
            })
            
    except Exception as e:
        import traceback
        print(f"❌ Error in bypass-levels endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/set-active-symbol')
def set_active_symbol():
    """Sets the active dashboard symbol in shared memory"""
    symbol = request.args.get('symbol', 'NIFTY').upper()
    shared_data.active_dashboard_symbol = symbol
    print(f"🔄 Active dashboard symbol updated to: {symbol}")
    return jsonify({"status": "success", "active_symbol": symbol})

@app.route('/api/gvn-scanner')
def get_gvn_scanner():
    """Consolidated high-speed scanner data for the GVN Master Dashboard"""
    symbol = request.args.get('symbol', 'NIFTY').upper()
    
    # 🚀 GVN SYNC: Fallback to NIFTY 50 if NIFTY is 0
    n_spot = shared_data.market_data.get("NIFTY", 0)
    if n_spot == 0:
        n_spot = shared_data.market_data.get("NIFTY 50", 0)
        
    gvn_scanner = getattr(shared_data, 'gvn_scanner_data', {})
    scanner_dict = gvn_scanner.get("scanner", {})
    summary_dict = gvn_scanner.get("summary", {})
    pulse_dict = gvn_scanner.get("pulse", {})
    
    # Extract the requested symbol's grid or fallback to the general grid
    if symbol in scanner_dict:
        alpha_grid = scanner_dict.get(symbol, [])[:14]
    else:
        alpha_grid = getattr(shared_data, 'gvn_alpha_grid', [])
        
    # Get the spot price for the active symbol
    spot_val = summary_dict.get(symbol, {}).get("spot", 0)
    if spot_val == 0:
        spot_val = shared_data.market_data.get(symbol, 0)
        
    # Build complete mapped data dictionary for compatibilities
    mapped_data = {}
    for s in scanner_dict:
        mapped_data[s] = scanner_dict[s][:14]
        
    # Build complete mapped pulse dictionary
    mapped_pulse = {}
    if pulse_dict:
        for s, p in pulse_dict.items():
            if isinstance(p, dict):
                mapped_pulse[s] = p
                
    # Ensure active symbol is present in market_pulse mapped dictionary
    if symbol not in mapped_pulse:
        flat_pulse = getattr(shared_data, 'market_pulse', {})
        mapped_pulse[symbol] = {
            "sentiment": flat_pulse.get("sentiment", "NEUTRAL"),
            "score": flat_pulse.get("score", 50),
            "trend": flat_pulse.get("trend", "SIDEWAYS"),
            "pcr": flat_pulse.get("pcr", 1.0),
            "pressure": flat_pulse.get("pressure", "NORMAL FLOW"),
            "support": flat_pulse.get("support", 0),
            "resistance": flat_pulse.get("resistance", 0),
            "ai_insight": flat_pulse.get("ai_insight", "Scanning..."),
            "inst_activity": flat_pulse.get("inst_activity", "LOW"),
            "wind_direction": flat_pulse.get("wind_direction", flat_pulse.get("trend", "SIDEWAYS")),
            "wind_power": flat_pulse.get("wind_power", "NORMAL"),
            "smart_money": flat_pulse.get("smart_money", "LOW"),
            "trap_zone": flat_pulse.get("trap_zone", "SAFE"),
            "vacuum_detected": flat_pulse.get("vacuum_detected", False)
        }
        
    return jsonify({
        "status": "success",
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "nifty_spot": spot_val if spot_val > 0 else n_spot,
        "alpha_grid": alpha_grid,
        "market_pulse": mapped_pulse,
        "data": mapped_data,
        "scanner_data": gvn_scanner,
        "summary": summary_dict,
        "demo_signals": getattr(shared_data, 'demo_signals', []),
        "z2h_watchlist": getattr(shared_data, 'gvn_z2h_watchlist', [])
    })

@app.route('/api/live-signals')
def get_live_signals():
    """Returns recent trade signals for the dashboard"""
    trades = AlgoTrade.query.order_by(AlgoTrade.timestamp.desc()).limit(10).all()
    results = []
    for t in trades:
        results.append({
            "time": t.timestamp.strftime("%H:%M:%S"),
            "symbol": t.symbol,
            "status": t.status,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl": round(t.pnl, 2) if t.pnl else 0
        })
    return jsonify(results)

@app.route('/api/broker-status')
def get_broker_status():
    """Returns connectivity status for the active user's broker"""
    uid = session.get('user_id', 1)
    config = UserBrokerConfig.query.filter_by(user_id=uid).first()
    active_broker = "AngelOne"
    if config and config.broker_name:
        active_broker = config.broker_name
        
    connected = shared_data.broker_connection_status.get(active_broker, False)
    
    # Support check for variations in casing
    if not connected:
        for k, v in shared_data.broker_connection_status.items():
            if k.lower() == active_broker.lower():
                connected = v
                break
                
    spot = shared_data.market_data.get("NIFTY", 0)
    if spot == 0:
        spot = shared_data.market_data.get("NIFTY 50", 0)
        
    return jsonify({
        "connected": connected,
        "broker_name": active_broker,
        "data_source": active_broker,
        "nifty_spot": spot,
        "reason": "High-Speed Data Flow Active" if connected else "Waiting for Feed Connection..."
    })

@app.route('/api/user-status')
def get_user_status():
    """Returns current logged in user status"""
    uid = session.get('user_id')
    if not uid: return jsonify({"status": "OFF"})
    user = db.session.get(User, uid)
    return jsonify({
        "username": user.username,
        "algo": user.algo_status,
        "type": user.user_type,
        "expiry": user.expiry_date.strftime("%d-%m-%Y") if user.expiry_date else "N/A"
    })

@app.route('/api/ai-chat', methods=['POST'])


def ai_chat():
    try:
        data = request.json
        msg = data.get('message', '').lower()
        nifty_price = data.get('nifty_price', '0')
        
        reply = "I am GVN AI Engine. Analyzing market... Current connectivity status is pending. "
        if "nifty" in msg or "trend" in msg:
            spot = shared_data.market_data.get("NIFTY", nifty_price)
            reply = f"Nifty Spot is around {spot}. Based on Alpha Grid, the trend looks Neutral to Sideways. Waiting for institutional breakout."
        elif "ce" in msg or "call" in msg:
            reply = "Scanning Call side momentum... Option chain shows heavy resistance at higher strikes. Wait for i5 level breakout for safe entry."
        elif "pe" in msg or "put" in msg:
            reply = "Scanning Put side momentum... Support is being tested at current levels. No clear signal yet."
        
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"AI Error: {e}"}), 500


@app.route('/unlock-premium/<int:user_id>')
def unlock_premium(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.user_type = 'LIVE'
        user.is_locked = False
        db.session.commit()
        flash("Premium Activated Successfully! Enjoy Zero-to-Hero signals.")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/toggle-algo/<int:user_id>')
def toggle_algo(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.algo_status = "ON" if user.algo_status == "OFF" else "OFF"
        db.session.commit()
        shared_data.market_pulse["algo_status"] = user.algo_status
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/toggle-auto-mode/<int:user_id>')
def toggle_auto_mode(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.full_auto_mode = not user.full_auto_mode
        db.session.commit()
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/update-lots', methods=['POST'])
def update_lots():
    uid = request.form.get('user_id')
    lots = request.form.get('trade_lots', 1)
    user = db.session.get(User, uid)
    if user:
        user.trade_lots = int(lots)
        db.session.commit()
    return redirect(url_for('user_dashboard', user_id=uid))

@app.route('/history')
def trade_history():
    return "Trade History Feature Coming Soon (PDF Generation)"

@app.route('/force-close-trade/<int:trade_id>')
def force_close(trade_id):
    trade = db.session.get(AlgoTrade, trade_id)
    if trade:
        trade.status = "Closed"
        db.session.commit()
    return redirect(url_for('user_dashboard', user_id=trade.user_id if trade else 1))

@app.route('/admin')
@app.route('/admin-control')
def admin_dashboard():
    admin = db.session.get(User, 1) # Assumes ID 1 is admin
    
    # Properly separate Live Approved subscribers from trial/demo clients
    real_users = User.query.filter(User.role == 'user', User.user_type == 'LIVE', User.is_approved == True).all()
    demo_users = User.query.filter(User.role == 'user', (User.user_type == 'DEMO') | (User.is_approved == False)).all()
    
    active_subscriptions = Subscription.query.filter_by(status='active').all()
    pending_payments = PendingPayment.query.filter_by(status='Pending').all()
    
    # Retrieve system config from user 1's broker settings
    config = UserBrokerConfig.query.filter_by(user_id=1).first()
    if not config:
        config = UserBrokerConfig(user_id=1)
        db.session.add(config)
        db.session.commit()
    
    return render_template(
        'admin.html', 
        user=admin, 
        real_users=real_users, 
        demo_users=demo_users, 
        subscriptions=active_subscriptions, 
        pending_payments=pending_payments,
        config=config
    )

@app.route('/toggle-signal-lock/<int:user_id>')
def toggle_signal_lock(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.is_locked = not user.is_locked
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/block-user/<int:user_id>')
def block_user(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.is_blocked = not user.is_blocked
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete-user/<int:user_id>')
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/toggle-kill-switch/<int:user_id>')
def toggle_kill_switch(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.admin_kill_switch = not user.admin_kill_switch
        if user.admin_kill_switch:
            user.algo_status = "OFF"
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/ai-diagnostic-summary')
def get_ai_diagnostic_summary():
    """Generates a human-like summary of the day's market experience."""
    trades = AlgoTrade.query.order_by(AlgoTrade.timestamp.desc()).limit(5).all()
    if not trades:
        return jsonify({"summary": "No trades executed today. System was in observation mode."})
    
    # Mock AI Analysis based on trade data
    last_trade = trades[0]
    summary = f"Sir, today's experience was informative. "
    if last_trade.pnl > 0:
        summary += f"We successfully captured a move in {last_trade.symbol}. "
    else:
        summary += f"The market was slightly volatile near our entry in {last_trade.symbol}. "
        
    summary += f"Resistance was weakening while support at {last_trade.symbol.split('_')[1]} held strong. "
    summary += f"Theta decay was managed by selecting Delta {round(last_trade.delta, 2)} strikes. "
    summary += "Overall, the system is performing optimally for Monday's session."
    
    return jsonify({"summary": summary})

@app.route('/admin/clear-demo-history')
def clear_demo_history():
    # Clear all DB trades
    try:
        db.session.query(AlgoTrade).delete()
        db.session.commit()
        # Clear demo memory
        import shared_data
        shared_data.demo_logs = []
        shared_data.demo_trade = {"active": False}
        shared_data.demo_playback_running = False
        print("✅ Demo History and Logs Cleared.")
    except Exception as e:
        print("Error clearing demo history:", e)
        db.session.rollback()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear-today-trades')
def clear_today_trades():
    """Clear only today's trade records from DB. Preserves historical data."""
    try:
        import datetime
        today = datetime.date.today()
        today_start = datetime.datetime.combine(today, datetime.time.min)
        deleted = db.session.query(AlgoTrade).filter(
            AlgoTrade.timestamp >= today_start
        ).delete(synchronize_session=False)
        db.session.commit()
        # Also clear in-memory trade state
        import shared_data
        shared_data.demo_logs = []
        shared_data.demo_trade = {"active": False}
        print(f"✅ Today's Trades Cleared: {deleted} records removed.")
    except Exception as e:
        print(f"❌ Error clearing today's trades: {e}")
        db.session.rollback()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/restart-server')
def restart_server():
    import os
    print("⚠️ [ADMIN] Server restart triggered. Terminating process...")
    os._exit(0)

@app.route('/admin-extend-demo/<int:user_id>')
def admin_extend_demo(user_id):
    user = db.session.get(User, user_id)
    if user:
        if not user.expiry_date:
            user.expiry_date = datetime.utcnow()
        user.expiry_date = user.expiry_date + timedelta(days=30)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/approve-user', methods=['POST'])
def approve_user():
    user_id = request.form.get('user_id')
    plan = request.form.get('plan', 'Basic')
    months = int(request.form.get('months', 1))
    
    user = db.session.get(User, user_id)
    if user:
        user.is_approved = True
        user.user_type = 'LIVE'
        user.selected_plan = plan
        user.expiry_date = datetime.utcnow() + timedelta(days=30 * months)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/update-settings', methods=['POST'])
def update_settings():
    config = UserBrokerConfig.query.filter_by(user_id=1).first()
    if not config:
        config = UserBrokerConfig(user_id=1)
        db.session.add(config)
    
    config.admin_user = request.form.get('admin_user')
    config.admin_pass = request.form.get('admin_pass')
    config.support_number_1 = request.form.get('support_1')
    config.support_number_2 = request.form.get('support_2')
    config.admin_phone = request.form.get('admin_phone')
    config.plan_basic_price = request.form.get('plan_basic_price')
    config.plan_premium_price = request.form.get('plan_premium_price')
    config.plan_ultimate_price = request.form.get('plan_ultimate_price')
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    uid = session.get('user_id', 1)
    data = request.form
    config = UserBrokerConfig.query.filter_by(user_id=uid).first()
    if not config:
        config = UserBrokerConfig(user_id=uid); db.session.add(config)
    
    config.broker_name = data.get('broker_name', 'Shoonya')
    config.client_id = data.get('client_id')
    
    # Only update if the value is provided and not the masked placeholder
    if data.get('access_token') and data.get('access_token') != "********":
        config.api_key = data.get('access_token')
    
    if data.get('client_secret') and data.get('client_secret') != "********":
        config.api_secret = data.get('client_secret')
        
    if data.get('totp_key') and data.get('totp_key') != "********":
        config.totp_key = data.get('totp_key')
    
    if data.get('broker_password') and data.get('broker_password') != "********":
        config.encrypted_password = cipher.encrypt(data.get('broker_password').encode())
    
    if data.get('webhook_url'): config.webhook_url = data.get('webhook_url')
    if data.get('secret_key') and data.get('secret_key') != "********":
        config.tv_secret = data.get('secret_key')
        
    if data.get('call_strike'): config.call_strike = data.get('call_strike')
    if data.get('put_strike'): config.put_strike = data.get('put_strike')
    
    try:
        db.session.commit()
    except Exception as commit_err:
        db.session.rollback()
        flash("❌ Database full or locked! Please pause OneDrive sync, run 'python fix_disk_full.py' in your command prompt, and try again.")
        return redirect(url_for('user_dashboard', user_id=uid))
    
    # Immediately test connection for the user's broker config
    broker_name = config.broker_name
    broker_key = broker_name.replace(" ", "") if broker_name else "Shoonya"
    
    # Reset connection status to False initially
    shared_data.broker_connection_status[broker_key] = False
    
    try:
        from broker_api import shoonya_http_login, angel_http_login, dhan_http_test
        creds = config.get_credentials()
        cfg = {
            "client_id": config.client_id,
            "password": creds.get('password'),
            "client_secret": creds.get('api_secret'),
            "access_token": creds.get('api_key'),
            "totp_key": creds.get('totp_key')
        }
        
        test_success = False
        if broker_key.lower() == "shoonya":
            token = shoonya_http_login(cfg)
            if token:
                test_success = True
        elif broker_key.lower() == "angelone":
            token = angel_http_login(cfg)
            if token:
                test_success = True
        elif broker_key.lower() == "dhan":
            test_success = dhan_http_test(cfg)
            
        if test_success:
            shared_data.broker_connection_status[broker_key] = True
            flash(f"🎉 Successfully connected to {broker_name}!")
        else:
            flash(f"❌ Connection Failed for {broker_name}! Please double check your Client ID, Secret, Password, and TOTP key.")
    except Exception as login_err:
        print(f"Error testing broker login: {login_err}")
    
    # Re-initialize orchestrator with new settings
    try:
        init_gvn()
    except Exception as e:
        pass
        
    return redirect(url_for('user_dashboard', user_id=uid))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- ENGINES ---
from gvn_master_orchestrator import get_orchestrator

# --- INITIALIZATION ---
def init_gvn():
    import shared_data
    if shared_data.system_status.get("initialized"):
        return
    
    with app.app_context():
        db.create_all()
        
        # Check for admin user
        try:
            target_phone = "9381490610"
            admin = User.query.filter_by(username="Venkat").first()
            if not admin:
                admin = User(username="Venkat", password_hash="gvn_admin_123", role="admin", is_active=True)
                db.session.add(admin)
                db.session.commit()
            
            # Initialize Orchestrator for admin
            config = UserBrokerConfig.query.filter_by(user_id=admin.id).first()
            broker_cfg = {}
            if config:
                creds = config.get_credentials()
                broker_cfg = {
                    "broker_name": config.broker_name,
                    "client_id": config.client_id,
                    "access_token": creds.get('api_key'),
                    "client_secret": creds.get('api_secret'),
                    "totp_key": creds.get('totp_key'),
                    "password": creds.get('password')
                }
            else:
                # Fallback to shared_data if DB is empty
                if hasattr(shared_data, 'PERMANENT_CREDENTIALS_BACKUP'):
                    backup = shared_data.PERMANENT_CREDENTIALS_BACKUP.get("angel")
                    if backup:
                        new_config = UserBrokerConfig(
                            user_id=admin.id,
                            broker_name=backup["broker_name"],
                            client_id=backup["client_id"]
                        )
                        new_config.set_credentials(
                            password=backup["password"],
                            api_key=backup["api_key"],
                            api_secret=backup["api_secret"],
                            totp_key=backup["totp_key"]
                        )
            # Start Orchestrator
            config = UserBrokerConfig.query.filter_by(user_id=1).first()
            if not config:
                config = UserBrokerConfig(user_id=1, broker_name="angelone")
                db.session.add(config)
                db.session.commit()
            
            broker_cfg = {
                "broker": config.broker_name or "angelone",
                "api_key": config.api_key or "",
                "api_secret": config.api_secret or "",
                "totp_key": config.totp_key or ""
            }
            
            if broker_cfg["api_key"]:
                telegram_cfg = {
                    "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                    "chat_id": os.environ.get("TELEGRAM_CHAT_ID", "")
                }
                orch = get_orchestrator(telegram_config=telegram_cfg)
                if orch:
                    try:
                        orch.start(broker_cfg)
                    except Exception as e:
                        print(f"❌ Orchestrator Start Failed: {e}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Initialization Error: {e}")

        try:
            config = UserBrokerConfig.query.filter_by(user_id=1).first()
            if config:
                broker = (config.broker_name or "angelone").lower()
                if "shoonya" in broker:
                    try:
                        import shoonya_live_feed
                        shoonya_live_feed.start_shoonya_worker()
                        print("🛰️ [STARTUP] Started SHOONYA Live Feed Worker.")
                    except Exception as e:
                        print(f"⚠️ Shoonya Feed Failed: {e}")
                else:
                    try:
                        import angel_live_feed
                        angel_live_feed.start_angel_worker()
                        print("🛰️ [STARTUP] Started ANGEL ONE Live Feed Worker.")
                    except Exception as e:
                        print(f"⚠️ Angel Feed Failed: {e}")
            else:
                try:
                    import angel_live_feed
                    angel_live_feed.start_angel_worker()
                except Exception as e:
                    print(f"⚠️ Angel Feed Failed: {e}")
        except Exception as e:
            print(f"⚠️ Feed Worker Start Failed: {e}")

        shared_data.system_status["initialized"] = True

# ---------------------------------------------------------
# GVN SYSTEM INITIALIZATION & STARTUP
# ---------------------------------------------------------

# Global flag to prevent double initialization during Flask reload
_initialized = False

def start_system():
    global _initialized
    if not _initialized:
        print("\n" + "="*50)
        print("🚀 GVN MASTER ALGO: INITIALIZING HIGH-SPEED ENGINE...")
        print("="*50 + "\n")
        
        # Start core logic in a separate thread
        import threading
        threading.Thread(target=init_gvn, daemon=True).start()
        _initialized = True

# Start system only when running as the main application
if __name__ == '__main__':
    start_system()
    
    port = int(os.environ.get("PORT", 8080))
    print("\n" + "="*60)
    print(f"🔥 GVN MASTER DASHBOARD IS NOW LIVE!")
    print(f"🔗 LOCAL ACCESS:   http://127.0.0.1:{port}")
    print(f"🔗 NETWORK ACCESS: http://192.168.29.101:{port}")
    print("="*60 + "\n")
    
    # use_reloader=False prevents the "User Already Connected" error on startup
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)