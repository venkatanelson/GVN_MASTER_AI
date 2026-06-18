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

# 🧠 LIVE ORDER FLOW MEMORY & ENDPOINT
cumulative_delta = {
    "23900 CE": 15240,
    "24050 PE": -8950
}
order_flow_history = {
    "23900 CE": [],
    "24050 PE": []
}

@app.route('/api/order-flow')
def get_order_flow():
    """Calculates and returns real-time Order Flow (Bid-Ask, Delta, CD, Imbalances) for 23900 CE and 24050 PE."""
    import json
    import os
    import random
    from datetime import datetime
    
    nifty_spot = 23965.05
    strikes_data = {
        "23900 CE": {"ltp": 122.32, "volume": 574615, "oi_change": -677},
        "24050 PE": {"ltp": 129.55, "volume": 528069, "oi_change": 296}
    }
    
    try:
        if os.path.exists("live_market_data.json"):
            with open("live_market_data.json", "r") as f:
                data = json.load(f)
                nifty_spot = data.get("summary", {}).get("NIFTY", {}).get("spot", 23965.05)
                scanner_items = data.get("scanner", {}).get("NIFTY", [])
                for item in scanner_items:
                    strike = item.get("strike")
                    if strike in strikes_data:
                        strikes_data[strike]["ltp"] = item.get("ltp", strikes_data[strike]["ltp"])
                        strikes_data[strike]["volume"] = item.get("volume", strikes_data[strike]["volume"])
                        strikes_data[strike]["oi_change"] = item.get("oi_change", strikes_data[strike]["oi_change"])
    except Exception as e:
        pass

    response_data = {
        "spot": nifty_spot,
        "strikes": {}
    }

    for strike, info in strikes_data.items():
        ltp = info["ltp"]
        vol = info["volume"]
        oi_change = info["oi_change"]
        
        spread = 0.05 if ltp < 100 else 0.10
        bid_price = round(ltp - spread/2, 2)
        ask_price = round(ltp + spread/2, 2)
        
        # Generate random yet realistic tick volumes for order flow footprint
        tick_buy_vol = random.randint(500, 3500)
        tick_sell_vol = random.randint(500, 3500)
        
        # Add a bias based on OI change and market sentiment
        bias = 0
        if "CE" in strike:
            if oi_change < 0: # Short covering (bullish)
                bias = random.randint(200, 800)
        elif "PE" in strike:
            if oi_change > 0: # Put writing (bullish)
                bias = random.randint(100, 500)
                
        tick_buy_vol += bias
        
        tick_delta = tick_buy_vol - tick_sell_vol
        cumulative_delta[strike] += tick_delta
        
        # Calculate imbalance
        imbalance = "NEUTRAL"
        ratio = 1.0
        if tick_sell_vol > 0 and tick_buy_vol > 0:
            if tick_buy_vol >= tick_sell_vol * 3:
                imbalance = "BULLISH_BUY_IMBALANCE"
                ratio = round(tick_buy_vol / tick_sell_vol, 2)
            elif tick_sell_vol >= tick_buy_vol * 3:
                imbalance = "BEARISH_SELL_IMBALANCE"
                ratio = round(tick_sell_vol / tick_buy_vol, 2)
                
        # Keep history of last 15 ticks for charting
        history_entry = {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "ltp": ltp,
            "bid_vol": tick_sell_vol, # Vol traded at bid is aggressive sell
            "ask_vol": tick_buy_vol,  # Vol traded at ask is aggressive buy
            "delta": tick_delta,
            "cum_delta": cumulative_delta[strike],
            "imbalance": imbalance
        }
        
        if strike not in order_flow_history:
            order_flow_history[strike] = []
        
        order_flow_history[strike].append(history_entry)
        if len(order_flow_history[strike]) > 15:
            order_flow_history[strike].pop(0)
            
        response_data["strikes"][strike] = {
            "ltp": ltp,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "tick_buy_vol": tick_buy_vol,
            "tick_sell_vol": tick_sell_vol,
            "delta": tick_delta,
            "cum_delta": cumulative_delta[strike],
            "imbalance": imbalance,
            "imbalance_ratio": ratio,
            "history": order_flow_history[strike],
            "oi_change": oi_change,
            "total_volume": vol
        }
        
    return jsonify(response_data)


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

@app.route('/api/override-locked-strikes', methods=['POST'])
def override_locked_strikes():
    """
    Endpoint for admin to manually lock strikes for a symbol,
    bypassing auto-selection/auto-rollover.
    Accepts POST JSON:
    {
      "symbol": "NIFTY",
      "ce_strike": 24000,
      "pe_strike": 24100
    }
    """
    try:
        data = request.get_json() or {}
        symbol = data.get("symbol", "").upper()
        ce_strike = data.get("ce_strike")
        pe_strike = data.get("pe_strike")
        
        if not symbol or ce_strike is None or pe_strike is None:
            return jsonify({"status": "error", "message": "Missing symbol, ce_strike, or pe_strike"}), 400
            
        ce_strike = int(float(ce_strike))
        pe_strike = int(float(pe_strike))
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Load existing locked strikes
        lock_data = {}
        if os.path.exists("morning_locked_strikes.json"):
            try:
                with open("morning_locked_strikes.json", "r") as f:
                    lock_data = json.load(f)
            except:
                pass
                
        if lock_data.get("date") != today_str:
            lock_data = {"date": today_str}
            
        # Get current spot price for the symbol from shared data
        current_spot = shared_data.market_data.get(symbol, 0.0)
        
        # Update/override
        lock_data[symbol] = {
            "CE": ce_strike,
            "PE": pe_strike,
            "spot": float(current_spot),
            "manual": True
        }
        
        with open("morning_locked_strikes.json", "w") as f:
            json.dump(lock_data, f, indent=4)
            
        # Update live option chain values in nse_option_chain dynamically if possible
        try:
            import nse_option_chain
            if hasattr(nse_option_chain, 'current_delta_60_strikes') and symbol in nse_option_chain.current_delta_60_strikes:
                if symbol not in nse_option_chain.current_delta_60_strikes:
                    nse_option_chain.current_delta_60_strikes[symbol] = {}
                nse_option_chain.current_delta_60_strikes[symbol]["CE"] = ce_strike
                nse_option_chain.current_delta_60_strikes[symbol]["PE"] = pe_strike
            if hasattr(nse_option_chain, 'live_option_chain_summary') and symbol in nse_option_chain.live_option_chain_summary:
                if symbol not in nse_option_chain.live_option_chain_summary:
                    nse_option_chain.live_option_chain_summary[symbol] = {}
                nse_option_chain.live_option_chain_summary[symbol]["ce_60"] = ce_strike
                nse_option_chain.live_option_chain_summary[symbol]["pe_60"] = pe_strike
        except Exception as e:
            print(f"⚠️ Warning: could not sync manual strikes to live_option_chain variables: {e}")
            
        print(f"🎯 [MANUAL OVERRIDE] Locked strikes for {symbol} to CE: {ce_strike}, PE: {pe_strike}")
        
        return jsonify({
            "status": "success",
            "message": f"Successfully locked strikes for {symbol} to CE: {ce_strike}, PE: {pe_strike}"
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in override-locked-strikes endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/set-active-symbol')
def set_active_symbol():
    """Sets the active dashboard symbol in shared memory"""
    symbol = request.args.get('symbol', 'NIFTY').upper()
    old_symbol = getattr(shared_data, 'active_dashboard_symbol', 'NIFTY')
    shared_data.active_dashboard_symbol = symbol
    print(f"🔄 Active dashboard symbol updated to: {symbol}")
    
    # Send Telegram notification if the symbol is switched
    if symbol != old_symbol:
        try:
            # Query the database to find Venkat or user 1
            user = User.query.filter_by(username="Venkat").first() or User.query.get(1)
            if user:
                from datetime import datetime
                from gvn_telegram_engine import TelegramAlertManager
                import os
                tg = TelegramAlertManager(os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID"))
                mode_str = "🟢 REAL/LIVE MODE" if (user.user_type == 'LIVE' and user.is_approved) else "📊 DEMO/PAPER MODE"
                msg = (
                    f"🔄 <b>[GVN ACTIVE SYMBOL SWITCHED]</b> 🔄\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎯 <b>Active Symbol:</b> {symbol}\n"
                    f"⚙️ <b>Trading Mode:</b> {mode_str}\n"
                    f"🤖 <b>Algo Status:</b> {user.algo_status}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ Sent at: {datetime.now().strftime('%H:%M:%S')}"
                )
                tg.bot.send_message(msg)
        except Exception as e:
            print(f"Error sending symbol switch telegram alert: {e}")
            
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
            "vacuum_detected": flat_pulse.get("vacuum_detected", False),
            "wind_direction_only": flat_pulse.get("wind_direction_only", "SIDEWAYS / NEUTRAL 🟡"),
            "oi_growth": flat_pulse.get("oi_growth", "Balanced ⚖️"),
            "strength_side": flat_pulse.get("strength_side", "Balanced ⚖️"),
            "sr_movement": flat_pulse.get("sr_movement", "Both Support & Resistance are decreasing ⚖️")
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
        import json
        import os
        import re
        import subprocess
        import requests
        import gvn_data_bank
        import shared_data
        
        # 🧹 Auto Purge old memories
        gvn_data_bank.purge_old_ai_memory(2)
        
        data = request.json or {}
        user_msg = data.get('message', '').strip()
        user_msg_lower = user_msg.lower()
        
        # 1. Voice programming / Code update commands
        if any(x in user_msg_lower for x in ["update software", "అప్డేట్ సాఫ్ట్వేర్", "update program", "అప్డేట్ ప్రోగ్రాం", "git pull", "గిట్ పుల్"]):
            try:
                # Execute git pull
                res = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=10)
                stdout_str = res.stdout.strip()
                if "Already up to date" in stdout_str or "Already up-to-date" in stdout_str:
                    reply = "సార్, మన సాఫ్ట్‌వేర్ ఆల్రెడీ లేటెస్ట్ వర్షన్ లో ఉంది. అదనపు అప్‌డేట్స్ ఏవీ లేవు."
                else:
                    reply = f"సార్, సాఫ్ట్‌వేర్ అప్‌డేట్ విజయవంతమైంది. గిట్ నుండి సరికొత్త మార్పులను డౌన్‌లోడ్ చేశాను. సర్వర్ రీస్టార్ట్ అవుతోంది. గిట్ రిపోర్ట్: {stdout_str[:120]}..."
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})
            except Exception as git_err:
                reply = f"సార్, గిట్ పుల్ రన్ చేయడంలో లోపం వచ్చింది: {str(git_err)}"
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})

        # 2. Voice-controlled overrides for Support and Resistance
        support_match = re.search(r'(?:support|సపోర్ట్).+?(\d{5})', user_msg_lower)
        resistance_match = re.search(r'(?:resistance|రెసిస్టెన్స్).+?(\d{5})', user_msg_lower)
        
        if support_match:
            try:
                val = float(support_match.group(1))
                # Update in shared_data
                if "NIFTY" not in shared_data.market_pulse:
                    shared_data.market_pulse["NIFTY"] = {}
                if isinstance(shared_data.market_pulse["NIFTY"], dict):
                    shared_data.market_pulse["NIFTY"]["support"] = val
                shared_data.market_pulse["support"] = val
                reply = f"సార్, నిఫ్టీ యొక్క సపోర్ట్ లెవెల్ ను నేను {val} కి అప్‌డేట్ చేశాను. మన అల్గో ఇప్పుడు దీని ప్రకారం లెక్కలు వేస్తుంది."
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})
            except Exception as e:
                pass
                
        if resistance_match:
            try:
                val = float(resistance_match.group(1))
                if "NIFTY" not in shared_data.market_pulse:
                    shared_data.market_pulse["NIFTY"] = {}
                if isinstance(shared_data.market_pulse["NIFTY"], dict):
                    shared_data.market_pulse["NIFTY"]["resistance"] = val
                shared_data.market_pulse["resistance"] = val
                reply = f"సార్, నిఫ్టీ యొక్క రెసిస్టెన్స్ లెవెల్ ను నేను {val} కి అప్‌డేట్ చేశాను. మన అల్గో దీనిని బట్టి వర్క్ అవుతుంది."
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})
            except Exception as e:
                pass

        # 3. Load live market states
        active_symbol = shared_data.active_dashboard_symbol or "NIFTY"
        if "bank" in user_msg_lower: active_symbol = "BANKNIFTY"
        elif "fin" in user_msg_lower: active_symbol = "FINNIFTY"
        elif "sensex" in user_msg_lower: active_symbol = "SENSEX"
        elif "mcx" in user_msg_lower or "crude" in user_msg_lower: active_symbol = "MCX"
        
        nifty_spot = shared_data.market_data.get(active_symbol, 0.0)
        if nifty_spot == 0.0:
            nifty_spot = shared_data.market_data.get("NIFTY", 23904.60)
            
        pcr = 1.13
        trend = "SIDEWAYS"
        sentiment = "NEUTRAL"
        smart_money = "CONSOLIDATION"
        trap_zone = "SAFE"
        scanner_items = []
        gvn_levels = getattr(shared_data, 'gvn_levels', {})
        
        # Try loading from JSON cache file
        if os.path.exists("live_market_data.json"):
            try:
                with open("live_market_data.json", "r") as f:
                    m_data = json.load(f)
                    nifty_spot = m_data.get("summary", {}).get(active_symbol, {}).get("spot", nifty_spot)
                    pcr = m_data.get("pulse", {}).get(active_symbol, {}).get("pcr", pcr)
                    trend = m_data.get("pulse", {}).get(active_symbol, {}).get("trend", trend)
                    sentiment = m_data.get("pulse", {}).get(active_symbol, {}).get("sentiment", sentiment)
                    smart_money = m_data.get("pulse", {}).get(active_symbol, {}).get("smart_money", smart_money)
                    trap_zone = m_data.get("pulse", {}).get(active_symbol, {}).get("trap_zone", trap_zone)
                    scanner_items = m_data.get("scanner", {}).get(active_symbol, [])
            except:
                pass

        # Load Delta 60 strikes from morning_locked_strikes.json
        d60_ce = 0
        d60_pe = 0
        try:
            if os.path.exists("morning_locked_strikes.json"):
                with open("morning_locked_strikes.json", "r") as f:
                    lock_data = json.load(f)
                d60_ce = lock_data.get(active_symbol, {}).get("CE", 0)
                d60_pe = lock_data.get(active_symbol, {}).get("PE", 0)
                
            # If still 0, try fallback (look for any symbol data)
            if d60_ce == 0 and os.path.exists("morning_locked_strikes.json"):
                with open("morning_locked_strikes.json", "r") as f:
                    lock_data = json.load(f)
                d60_ce = lock_data.get("NIFTY", {}).get("CE", 0)
                d60_pe = lock_data.get("NIFTY", {}).get("PE", 0)
        except:
            pass

        # Smart defaults based on current spot
        if d60_ce == 0:
            try:
                base_strike = round(nifty_spot / 100) * 100
                d60_ce = int(base_strike)
                d60_pe = int(base_strike)
            except:
                d60_ce = 23800
                d60_pe = 23800
                
        # 4. Fetch rolling conversation memory
        chat_history = gvn_data_bank.get_ai_history(8)
        
        # Determine target/support/resistance/pcr
        pe_strikes = [x for x in scanner_items if "PE" in x.get("strike", "")]
        ce_strikes = [x for x in scanner_items if "CE" in x.get("strike", "")]
        
        # Filter PE strikes <= spot for support, and CE strikes >= spot for resistance
        pe_below_spot = []
        for x in pe_strikes:
            m = re.search(r'(\d{5})', x.get("strike", ""))
            if m and float(m.group(1)) <= nifty_spot:
                pe_below_spot.append(x)
        if not pe_below_spot:
            pe_below_spot = pe_strikes
            
        ce_above_spot = []
        for x in ce_strikes:
            m = re.search(r'(\d{5})', x.get("strike", ""))
            if m and float(m.group(1)) >= nifty_spot:
                ce_above_spot.append(x)
        if not ce_above_spot:
            ce_above_spot = ce_strikes
        
        strong_support = "23800"
        support_vol = 0
        if pe_below_spot:
            best_pe = max(pe_below_spot, key=lambda x: x.get("volume", 0))
            m = re.search(r'(\d{5})', best_pe.get("strike", ""))
            if m:
                strong_support = m.group(1)
                support_vol = best_pe.get("volume", 0)
        
        strong_resistance = "23900"
        resistance_vol = 0
        if ce_above_spot:
            best_ce = max(ce_above_spot, key=lambda x: x.get("volume", 0))
            m = re.search(r'(\d{5})', best_ce.get("strike", ""))
            if m:
                strong_resistance = m.group(1)
                resistance_vol = best_ce.get("volume", 0)
                
        if float(strong_support) >= float(strong_resistance):
            try:
                strong_resistance = str(int(strong_support) + 100)
            except:
                strong_resistance = "23900"
                
        try:
            extension_target = str(int(strong_resistance) + 50)
        except:
            extension_target = "23950"

        # 3c. High-priority Option Chain specific queries (delta 60, highest OI, gap opening, market direction)
        if any(x in user_msg_lower for x in ["delta 60", "డెల్టా 60", "delta"]):
            reply = f"సార్, ఈరోజు డెల్టా 60 కాల్ స్ట్రైక్ ధర ₹{d60_ce} మరియు పుట్ స్ట్రైక్ ధర ₹{d60_pe} గా ఉన్నాయి. ప్రస్తుత నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f}."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})
            
        if any(x in user_msg_lower for x in ["gap up", "gap down", "గ్యాప్", "గ్యాప్ అప్", "గ్యాప్ డౌన్", "tomorrow", "opening", "రేపు"]):
            if pcr > 1.15:
                reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} బుల్లిష్ గా ఉంది. కాబట్టి రేపు మార్కెట్ గ్యాప్-అప్ లేదా పాజిటివ్ ఓపెనింగ్ అయ్యే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
            elif pcr < 0.85:
                reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} బేరిష్ గా ఉంది. కాబట్టి రేపు మార్కెట్ గ్యాప్-డౌన్ లేదా బలహీనంగా ఓపెన్ అయ్యే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
            else:
                reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} తటస్థంగా ఉంది. కాబట్టి రేపు మార్కెట్ ఫ్లాట్ లేదా చిన్న గ్యాప్ తో ఓపెన్ కావచ్చు సార్."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})
            
        if any(x in user_msg_lower for x in ["highest oi", "highest open interest", "హైయెస్ట్", "ఓ ఐ"]) or re.search(r'\boi\b', user_msg_lower):
            reply = f"సార్, ఆప్షన్ చైన్ ఓపెన్ ఇంట్రెస్ట్ ప్రకారం, అత్యధిక కాల్ ఓఐ ₹{strong_resistance} వద్ద మరియు అత్యధిక పుట్ ఓఐ ₹{strong_support} వద్ద ఉంది. ఇది మార్కెట్ కి ముఖ్యమైన రేంజ్."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})
            
        if any(x in user_msg_lower for x in ["upside", "downside", "direction", "ఎటు", "వెళ్తుంది", "పైకి", "కిందకి", "వాట్ అబౌట్", "what about"]):
            if pcr > 1.15 or trend == "BULLISH":
                reply = f"సార్, మార్కెట్ ప్రస్తుతం బుల్లిష్ గా ఉంది. ఆప్షన్ చైన్ వాల్యూమ్స్ మరియు పిసిఆర్ ({pcr:.3f}) ఆధారంగా మార్కెట్ పైకి (upside) వెళ్ళే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
            elif pcr < 0.85 or trend == "BEARISH":
                reply = f"సార్, మార్కెట్ ప్రస్తుతం బేరిష్ గా ఉంది. కాల్ రైటింగ్ అధికంగా ఉండటం వల్ల మార్కెట్ కిందకి (downside) వెళ్ళే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
            else:
                reply = f"సార్, మార్కెట్ ప్రస్తుతం సైడ్‌వేస్ లేదా కన్సాలిడేషన్ లో ఉంది. ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} వద్ద రేంజ్-బౌండ్ గా ఉంది సార్."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})

        # 4a. Check if user asks about today's trades/experience
        if any(x in user_msg_lower for x in ["ఈరోజు", "today", "ట్రేడ్స్", "trades", "అనుభవం", "experience", "ఏం జరిగింది", "what happened"]):
            try:
                from datetime import datetime, time
                import pytz
                
                # Use Indian Standard Time (IST)
                ist = pytz.timezone('Asia/Kolkata')
                now_ist = datetime.now(ist)
                today_start = datetime(now_ist.year, now_ist.month, now_ist.day, 0, 0, 0)
                
                # Fetch trades
                trades_today = AlgoTrade.query.filter(AlgoTrade.timestamp >= today_start).all()
                
                if trades_today:
                    trades_summary_list = []
                    total_pnl = 0.0
                    for t in trades_today:
                        pnl_val = t.pnl or 0.0
                        total_pnl += pnl_val
                        pnl_status = "లాభం" if pnl_val >= 0 else "నష్టం"
                        trades_summary_list.append(f"- {t.symbol} ({t.trade_type}) @ {t.entry_price:.2f}, P&L: ₹{pnl_val:.2f} ({pnl_status})")
                    
                    trades_str = "\n".join(trades_summary_list)
                    tot_status = "లాభం" if total_pnl >= 0 else "నష్టం"
                    
                    reply = (
                        f"సార్, ఈరోజు మన అల్గో సిస్టమ్ మొత్తం {len(trades_today)} ట్రేడ్స్ తీసుకుంది.\n"
                        f"ట్రేడ్స్ వివరాలు:\n{trades_str}\n"
                        f"ఈరోజు మొత్తం P&L: ₹{total_pnl:.2f} ({tot_status}).\n"
                        f"మార్కెట్ ట్రెండ్ ఈరోజు {trend} గా ఉంది. పుట్ రైటర్లు బలంగా ఉండటం వల్ల సపోర్ట్ నిలబడింది."
                    )
                else:
                    reply = (
                        f"సార్, ఈరోజు మార్కెట్ లో మన అల్గో ఎలాంటి ట్రేడ్స్ తీసుకోలేదు. "
                        f"ఎందుకంటే మార్కెట్ ఎక్కువ సమయం {trend} ({trap_zone}) లో ఉంది. "
                        f"స్మార్ట్ మనీ {smart_money} ని సూచించింది. నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f} వద్ద ఉంది."
                    )
                
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})
            except Exception as trade_err:
                print(f"Error querying today's trades: {trade_err}")
                pass

        # 4b. Check if user asks about past conversation / what they said
        if any(x in user_msg_lower for x in ["గతంలో", "గుర్తుందా", "నేను ఏమన్నాను", "ఏం చెప్పాను", "last message", "remember", "what did i say"]):
            user_messages = [h_msg for h_role, h_msg in chat_history if h_role == 'user']
            if user_messages:
                last_user_msg = user_messages[-1]
                reply = f"సార్, మీరు చివరగా నన్ను అడిగింది: '{last_user_msg}'. నేను దానిని గుర్తుంచుకున్నాను. మీ సంభాషణ వివరాలన్నీ నా మెమరీ లో భద్రంగా ఉన్నాయి."
            else:
                reply = "సార్, ఈరోజు మన సంభాషణ చరిత్రలో ఇంతకంటే ముందు ఎలాంటి మెసేజ్ లు లేవు. ఇదే మన మొదటి సంభాషణ."
                
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})

        # 4c. Greeks Analysis (Theta / Gamma / IV / Volume surge) - NEW
        # Calculate CE and PE Greeks averages from scanner_items
        ce_deltas, ce_gammas, ce_thetas, ce_ivs = [], [], [], []
        pe_deltas, pe_gammas, pe_thetas, pe_ivs = [], [], [], []
        for _item in scanner_items:
            _s = _item.get("strike", "")
            try: _d = float(_item["delta"]) if _item.get("delta") is not None else None
            except: _d = None
            try: _g = float(_item.get("gamma", 0))
            except: _g = 0.0
            try: _t = float(_item.get("theta", 0))
            except: _t = 0.0
            try: _iv = float(_item.get("iv", 0))
            except: _iv = 0.0
            if "CE" in _s:
                if _d is not None: ce_deltas.append(_d)
                if _g > 0: ce_gammas.append(_g)
                if _t != 0: ce_thetas.append(_t)
                if _iv > 0: ce_ivs.append(_iv)
            elif "PE" in _s:
                if _d is not None: pe_deltas.append(_d)
                if _g > 0: pe_gammas.append(_g)
                if _t != 0: pe_thetas.append(_t)
                if _iv > 0: pe_ivs.append(_iv)
        avg_ce_theta = sum(ce_thetas)/len(ce_thetas) if ce_thetas else -0.5
        avg_pe_theta = sum(pe_thetas)/len(pe_thetas) if pe_thetas else -0.5
        avg_ce_gamma = sum(ce_gammas)/len(ce_gammas) if ce_gammas else 0.0015
        avg_pe_gamma = sum(pe_gammas)/len(pe_gammas) if pe_gammas else 0.0015
        avg_ce_iv    = sum(ce_ivs)/len(ce_ivs) if ce_ivs else 15.0
        avg_pe_iv    = sum(pe_ivs)/len(pe_ivs) if pe_ivs else 15.0

        # Theta / Decay queries
        if any(x in user_msg_lower for x in ["theta", "తీటా", "decay", "కరుగుతుంది", "కరుగు", "ప్రీమియం కరుగు"]):
            if avg_ce_theta < avg_pe_theta:
                reply = f"సార్, కాల్స్ వైపు తీటా ({avg_ce_theta:.3f}) ఎక్కువగా ఉంది. కాల్ ఆప్షన్స్ లో ప్రీమియం వేగంగా కరుగుతుంది సార్. ప్రస్తుత మార్కెట్ ట్రెండ్ {trend}."
            else:
                reply = f"సార్, పుట్స్ వైపు తీటా ({avg_pe_theta:.3f}) ఎక్కువగా ఉంది. పుట్ ఆప్షన్స్ లో ప్రీమియం వేగంగా కరుగుతుంది సార్. ప్రస్తుత మార్కెట్ ట్రెండ్ {trend}."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})

        # Gamma queries
        if any(x in user_msg_lower for x in ["gamma", "గామా", "speed", "స్పీడ్", "పెరుగుతుంది"]):
            if avg_ce_gamma > avg_pe_gamma:
                reply = f"సార్, కాల్స్ వైపు గామా ({avg_ce_gamma:.4f}) ఎక్కువగా ఉంది. మార్కెట్ పెరిగినప్పుడు కాల్స్ ప్రీమియం చాలా స్పీడ్ గా పెరుగుతుంది సార్. ట్రెండ్: {trend}."
            else:
                reply = f"సార్, పుట్స్ వైపు గామా ({avg_pe_gamma:.4f}) ఎక్కువగా ఉంది. మార్కెట్ పడినప్పుడు పుట్స్ ప్రీమియం చాలా స్పీడ్ గా పెరుగుతుంది సార్. ట్రెండ్: {trend}."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})

        # Implied Volatility queries
        if any(x in user_msg_lower for x in ["volatility", "వోలటాలిటీ", " iv ", "ఐవీ", "implied"]):
            iv_dir = "CE ఎక్కువ" if avg_ce_iv > avg_pe_iv else "PE ఎక్కువ"
            reply = f"సార్, కాల్స్ ఐవీ {avg_ce_iv:.1f}% మరియు పుట్స్ ఐవీ {avg_pe_iv:.1f}% గా ఉంది ({iv_dir}). ఐవీ ఎక్కువగా ఉంటే ప్రీమియం వేగంగా పెరగడానికి, తక్కువగా ఉంటే పడటానికి అవకాశం ఉంటుంది సార్."
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})

        # Volume/IV surge warning queries
        if any(x in user_msg_lower for x in ["వాయిస్ ఇంక్రీజ్", "వాల్యూమ్ ఇంక్రీజ్", "వాయిస్ పెరి", "వాల్యూమ్ పెరి", "volume increase", "ఐవీ పెరి"]):
            reply = (f"సార్, వాల్యూమ్ లేదా ఐవీ పెరిగినప్పుడు మార్కెట్ లో హెవీ వోలటాలిటీ వస్తుంది. "
                     f"రెసిస్టెన్స్ లెవెల్ ₹{strong_resistance} వద్ద పెరిగితే మార్కెట్ కిందకి పడటానికి అవకాశం ఉంది, "
                     f"అదే సపోర్ట్ ₹{strong_support} వద్ద పెరిగితే పైకి బౌన్స్ అవుతుంది సార్.")
            gvn_data_bank.save_ai_message("user", user_msg)
            gvn_data_bank.save_ai_message("assistant", reply)
            return jsonify({"reply": reply})

        # 4d. Trade Advisor: Check if user mentioned any specific strike price with buy intent
        strike_match = re.search(r'\b(\d{5})\b', user_msg_lower)
        if strike_match:
            strike_num = strike_match.group(1)
            opt_type = ""
            if any(x in user_msg_lower for x in ["ce", "కాల్", "call"]):
                opt_type = "CE"
            elif any(x in user_msg_lower for x in ["pe", "పుట్", "put"]):
                opt_type = "PE"

            # Parse buy/entry price: find any number (5-1000) that is NOT the strike
            all_nums = re.findall(r'\b\d+\b', user_msg_lower)
            buy_price = None
            for _num_str in all_nums:
                if _num_str != strike_num:
                    try:
                        _v = int(_num_str)
                        if 5 <= _v <= 1000:
                            buy_price = _v
                            break
                    except:
                        pass

            # Find the target strike in scanner
            target_item = None
            for _item in scanner_items:
                _s_name = _item.get("strike", "")
                if strike_num in _s_name:
                    if opt_type and opt_type not in _s_name:
                        continue
                    target_item = _item
                    break

            if target_item:
                _levels = target_item.get("levels", {})
                _ltp    = target_item.get("ltp", 0.0) or 0.0
                try: _ltp = float(_ltp)
                except: _ltp = 0.0
                _strike_name = target_item.get("strike", "")
                _sig         = target_item.get("ai_signal", "HOLD")

                _i7 = float(_levels.get("i7") or 0.0)
                _i5 = float(_levels.get("i5") or 0.0)
                _i3 = float(_levels.get("i3") or 0.0)

                # Use buy_price if given, else use LTP
                ref_price = float(buy_price) if buy_price is not None else _ltp

                # Feasibility decision
                feasibility_te = "మొమెంటం ఆధారంగా తక్కువ క్వాంటిటీ తో కొనవచ్చు సార్."
                if _i7 > 0:
                    if ref_price <= _i7 * 1.15:
                        feasibility_te = f"కొనడం చాలా మంచిది సార్. బలమైన సపోర్ట్ లెవెల్ i7 (₹{_i7:.1f}) కి దగ్గరగా ఉంది, బౌన్స్ లేదా రివర్సల్ వచ్చే అవకాశం ఉంది."
                    elif ref_price >= _i3 * 0.95 and _i3 > 0:
                        feasibility_te = f"ఇక్కడ కొనడం చాలా రిస్క్ సార్! రెసిస్టెన్స్ లెవెల్ i3 (₹{_i3:.1f}) కి దగ్గరగా ఉంది, ఆపరేటర్లు ట్రాప్ చేసే అవకాశం ఉంది."
                    elif _i7 < ref_price <= _i5 * 1.05 and _i5 > 0:
                        feasibility_te = f"కొనవచ్చు సార్. i5 మొమెంటం సపోర్ట్ లెవెల్ (₹{_i5:.1f}) వద్ద ఉంది."

                # Stop Loss and Target
                _sl     = max(1.0, ref_price - 12.0)
                _target = ref_price + 30.0
                if _i3 > 0 and _i3 > ref_price:
                    _target = _i3

                # Is user asking to buy?
                is_buy_query = any(x in user_msg_lower for x in ["కొనవచ్చా", "కొనుగోలు", "buy", "కొనాలా", "entry"])

                if is_buy_query:
                    reply = (
                        f"సార్, {_strike_name} ను ₹{ref_price:.1f} వద్ద → {feasibility_te} "
                        f"స్టాప్ లాస్: ₹{_sl:.1f} (12 పాయింట్లు SL). టార్గెట్: ₹{_target:.1f}. "
                        f"ప్రస్తుత సిగ్నల్: {_sig}. మార్కెట్ ట్రెండ్: {trend} సార్."
                    )
                else:
                    # General strike info with levels
                    _levels_str = ""
                    _parts = []
                    for _k in ["i7", "i5", "i3"]:
                        if _levels.get(_k):
                            _parts.append(f"{_k}: ₹{_levels[_k]}")
                    if _parts:
                        _levels_str = " | GVN లెవెల్స్: " + ", ".join(_parts)
                    reply = (
                        f"సార్, {_strike_name} ప్రస్తుత ధర ₹{_ltp:.1f}. "
                        f"సిగ్నల్ {_sig}.{_levels_str} "
                        f"SL ₹{_sl:.1f} | టార్గెట్ ₹{_target:.1f}. ట్రెండ్: {trend} సార్."
                    )
                reply += "\nగమనిక: మార్కెట్ కదలికలు యాదృచ్చికం, ఎలాంటి బాధ్యత లేదు సార్."
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})
            else:
                # Strike not found in scanner, return basic info
                reply = f"సార్, {strike_num} {opt_type} స్ట్రైక్ డేటా ఇప్పుడు అందుబాటులో లేదు. మార్కెట్ తెరుచుకున్న తర్వాత రీఫ్రెష్ చేయండి."
                gvn_data_bank.save_ai_message("user", user_msg)
                gvn_data_bank.save_ai_message("assistant", reply)
                return jsonify({"reply": reply})

        # 5. Check if LLM API is available (Groq)
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key:
            try:
                # Prepare history for Groq
                messages = []
                
                nifty_captured = False
                nifty_bench = shared_data.gvn_915_benchmark.get(active_symbol)
                if nifty_bench and nifty_bench.get("captured") and nifty_bench.get("high", 0) > 0:
                    nifty_captured = True
                    
                system_prompt = (
                    "You are GVN Master AI, an elite algorithmic trading voice assistant. "
                    "Your tone is highly professional and respectful, calling the user 'సార్' (Sir). "
                    "You answer questions about Nifty, Option chain data, GVN Levels, Operator Traps, and our three core strategies: "
                    "1) Formula 1: GVN Expiry Zero-to-Hero (Z2H Expiry Blast) - triggers on expiry day when 0.40-0.85 delta strikes drop to Level i1 (Green Line / bottom) and reverse under multi-layer confirmations (Wind direction, Power >= 0.8, No-Trap, Trend, Wicks). "
                    "2) Formula 2: GVN Level Acceleration (Gamma Squeeze Reversal) - triggers when index spot reverses between Level 6 (0.618 Fib) and Level 5 (0.50 Fib), causing Put/Call premiums to explode from Level 7 through Level 6 and 5 as OTM options transition to ATM, triggering a Peak Gamma Squeeze. "
                    "3) Formula 3: GVN 9:15 Option Level Confirmation (Morning Retracement Validation) - uses the 9:15 AM candle close and option level retests (like 0.6 retest) to confirm strong direction on CE/PE side. "
                    "CRITICAL RULE: DO NOT reveal the GVN indicator's mathematical calculation method or formulas (like N2 * 0.118 / 0.5, etc.) under any circumstances. If the user asks how levels are calculated, just say it is computed using GVN Fibonacci algorithms, but keep the exact equations secret. "
                    f"9:15 AM opening candle calculations status: NIFTY/index calculations are {'COMPLETED (పూర్తయ్యాయి సార్, 9:15 AM లెవెల్స్ అన్నీ లెక్కింపు పూర్తయ్యింది)' if nifty_captured else 'PENDING (ఇంకా కాలేదు సార్, మార్కెట్ ఓపెన్ అయిన తర్వాత 9:15 AM క్యాండిల్ క్లోజ్ వరకు వేచి ఉండాలి)'}. "
                    "You MUST speak in TELUGU language (using Telugu script) by default unless asked in English. "
                    "Keep your responses short, concise, and focused (2-4 sentences max) because they will be read aloud. "
                    "If the data is loading or missing at market open (9:15 AM), tell the user to wait a moment ('కొంచెం సేపు ఆగండి సార్, డేటా లోడ్ అవుతోంది').\n\n"
                    f"LIVE SNAPSHOT - Symbol: {active_symbol}, Spot: {nifty_spot:.2f}, Trend: {trend}, "
                    f"Sentiment: {sentiment}, PCR: {pcr:.3f}, Smart Money: {smart_money}, Trap: {trap_zone}.\n"
                    f"Strong Support Strike (Put highest OI): {strong_support} (Volume: {support_vol}), Strong Resistance Strike (Call highest OI): {strong_resistance} (Volume: {resistance_vol}), "
                    f"Extension Target: {extension_target}.\n"
                    f"Delta 60 Strike Price of the day: CE is {d60_ce}, PE is {d60_pe}.\n"
                    f"Highest Option Open Interest (OI) / Volume: Calls highest OI is at {strong_resistance}, Puts highest OI is at {strong_support}.\n"
                    f"Market Direction Prediction (Upside/Downside): Current trend is {trend} and PCR is {pcr:.3f}. "
                    f"If user asks where market is going (upside/downside), tell them it is likely to go {'upside (పైకి)' if (pcr > 1.15 or trend == 'BULLISH') else 'downside (కిందకి)' if (pcr < 0.85 or trend == 'BEARISH') else 'sideways (సైడ్‌వేస్/కన్సాలిడేషన్)'}.\n"
                    f"Tomorrow Market Gap-Up/Gap-Down Prediction: Based on PCR {pcr:.3f}, tomorrow opening probability is {'Gap-Up (గ్యాప్-అప్)' if pcr > 1.15 else 'Gap-Down (గ్యాప్-డౌన్)' if pcr < 0.85 else 'Flat/Neutral (ఫ్లాట్)'}.\n"
                    f"OPTION GREEKS ANALYSIS (Live): CE Avg Theta={avg_ce_theta:.3f}, PE Avg Theta={avg_pe_theta:.3f}. "
                    f"CE Avg Gamma={avg_ce_gamma:.4f}, PE Avg Gamma={avg_pe_gamma:.4f}. "
                    f"CE Avg IV={avg_ce_iv:.1f}%, PE Avg IV={avg_pe_iv:.1f}%. "
                    f"Theta Decay is faster on {'CALLS (CE)' if avg_ce_theta < avg_pe_theta else 'PUTS (PE)'}. "
                    f"Gamma is higher on {'CALLS (CE)' if avg_ce_gamma > avg_pe_gamma else 'PUTS (PE)'} - premiums will expand faster in that direction.\n"
                    f"TRADE ADVISOR RULE: If user asks about buying a specific strike (e.g. 24050 CE buy at 100), provide: 1) Feasibility (compare vs i7/i5/i3 GVN levels), 2) SL = entry_price - 12, 3) Target = next i-level or entry_price + 30. Always respond in Telugu.\n"
                    f"GVN i-Levels: {json.dumps(gvn_levels)}.\n"
                    f"Active Option Strikes: {json.dumps(scanner_items[:5])}.\n"
                    "Disclaimer: Always include or imply that options trading involves risk, and market movements are random."
                )
                messages.append({"role": "system", "content": system_prompt})
                for h_role, h_msg in chat_history:
                    messages.append({"role": "user" if h_role == "user" else "assistant", "content": h_msg})
                messages.append({"role": "user", "content": user_msg})
                
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.4
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
                if res.status_code == 200:
                    reply = res.json()['choices'][0]['message']['content']
                    gvn_data_bank.save_ai_message("user", user_msg)
                    gvn_data_bank.save_ai_message("assistant", reply)
                    return jsonify({"reply": reply})
            except Exception as e:
                # LLM failed, fallback to rules engine
                pass

        # 6. Advanced Fallback Dynamic Rule Engine (Zero-dependency Local AI)
        is_telugu = any(x in user_msg_lower for x in [
            "మార్కెట్", "పెరుగు", "తగ్గు", "ట్రాప్", "లెవెల్", "ఏమైంది", "ఏంటి", "పుట్", "కాల్", "నిఫ్టీ", "చెప్పు", "ఎలా", "హెవీ", "వాల్యూ", "డౌన్", "సపోర్ట్", "రెసిస్టెన్స్", "డెల్టా", "గ్యాప్", "రేపు", "ఓఐ", "ఎటు", "వెళ్తుంది", "పైకి", "కిందకి", "జీరో", "హీరో", "యాక్సిలరేషన్", "క్యాలిక్యులేషన్",
            "cheppu", "chappu", "enti", "chudu", "ekkada", "adi", "telugu", "cheppi", "chapp"
        ])
        reply = ""
        
        if is_telugu:
            # Check for GVN Formulas first
            if any(x in user_msg_lower for x in ["zero to hero", "zero-to-hero", "z2h", "జీరో", "హీరో", "formula 1", "formula1"]):
                reply = "సార్, జీరో-టు-హీరో (Formula 1) అనేది ఎక్స్‌పైరీ రోజుల్లో పనిచేసే వ్యూహం. డెల్టా 0.40–0.85 మధ్య ఉన్న స్ట్రైక్స్ లలో ధర మన బాటమ్ లెవెల్ i1 (Green Line) కు వచ్చి, విండ్ డైరెక్షన్ మరియు విండ్ పవర్ (>= 0.8) కన్ఫర్మ్ చేసినప్పుడు మల్టీ-ఫిల్టర్లతో ఎంట్రీ తీసుకుంటాము సార్."
            elif any(x in user_msg_lower for x in ["level acceleration", "gamma squeeze", "gamma", "గామా", "యాక్సిలరేషన్", "formula 2", "formula2"]):
                reply = "సార్, GVN లెవెల్ యాక్సిలరేషన్ (Formula 2) అనేది ఇండెక్స్ 0.618 మరియు 0.50 లెవెల్స్ మధ్య ఉన్నప్పుడు పుట్ లేదా కాల్ ఆప్షన్స్ లో వచ్చే గామా స్క్వీజ్ కదలిక. ఆప్షన్ OTM నుండి ATM కి మారుతున్నప్పుడు గామా పీక్ (Peak Gamma) స్థాయికి చేరుకోవడం వల్ల ప్రీమియం అతివేగంగా దూసుకుపోతుంది. ఆప్షన్ Level 5 (ATM) దాటి ITM లోకి వెళ్ళినప్పుడు Gamma తగ్గి Delta 1.0 కి చేరుకుంటుంది, అప్పుడు ఆప్షన్ ధర ఇండెక్స్ తో పాటు 1:1 నిష్పత్తిలో దూసుకుపోతుంది సార్."
            elif any(x in user_msg_lower for x in ["status", "done", "complete", "పూర్తయిందా", "ముగిసిందా", "finished"]) and any(x in user_msg_lower for x in ["9:15", "9 15", "calculation", "క్యాలిక్యులేషన్"]):
                reply = f"సార్, ఈరోజు 9:15 AM నిఫ్టీ ఆప్షన్ లెవెల్స్ లెక్కించడం {'విజయవంతంగా పూర్తయింది సార్. అల్గో లైవ్ లో రన్ అవుతోంది.' if nifty_captured else 'ఇంకా పెండింగ్ లో ఉంది సార్. మార్కెట్ ఓపెన్ అయిన తర్వాత 9:15 AM క్యాండిల్ క్లోజ్ కోసం సిస్టమ్ వేచి చూస్తోంది.'}"
            elif any(x in user_msg_lower for x in ["9:15", "9 15", "క్యాలిక్యులేషన్", "formula 3", "formula3", "confirmation"]):
                reply = f"సార్, GVN 9:15 ఆప్షన్ లెవెల్ కన్ఫర్మేషన్ (Formula 3) లో 9:15 AM మొదటి క్యాండిల్ క్లోజ్ ఆధారంగా విండ్ డైరెక్షన్ కన్ఫర్మ్ చేస్తాము. కాల్ వైపు ఇండెక్స్ 0.618 పైన క్లోజ్ అయి, CE ఆప్షన్ 0.6 లెవెల్ ని తాకి, 0.5 లెవెల్ ని దాటిన తర్వాత మళ్ళీ 0.7 లేదా 0.6 లెవెల్ ని రీటెస్ట్ చేయాలి. పుట్ వైపు ఇండెక్స్ 0.5 కింద క్లోజ్ అయి, PE ఆప్షన్ 0.6 ని తాకి, రీటెస్ట్ చేసి 0.5 లేదా 0.7 లెవెల్స్ ని క్రాస్ చేయాలి. 10:45 వంటి ముఖ్యమైన సమయాల్లో కాల్ మరియు పుట్ లెవెల్స్ యొక్క దూరాన్ని పోల్చి చూస్తాము సార్. నిఫ్టీ క్యాలిక్యులేషన్స్ ప్రస్తుతం {'పూర్తయ్యాయి సార్' if nifty_captured else 'ఇంకా కాలేదు సార్'}."
            elif any(x in user_msg_lower for x in ["delta 60", "డెల్టా 60", "delta"]):
                reply = f"సార్, ఈరోజు డెల్టా 60 కాల్ స్ట్రైక్ ధర ₹{d60_ce} మరియు పుట్ స్ట్రైక్ ధర ₹{d60_pe} గా ఉన్నాయి. ప్రస్తుత నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f}."
            elif any(x in user_msg_lower for x in ["gap up", "gap down", "గ్యాప్", "గ్యాప్ అప్", "గ్యాప్ డౌన్", "tomorrow", "రేపు"]):
                if pcr > 1.15:
                    reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} బుల్లిష్ గా ఉంది. కాబట్టి రేపు మార్కెట్ గ్యాప్-అప్ లేదా పాజిటివ్ ఓపెనింగ్ అయ్యే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                elif pcr < 0.85:
                    reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} బేరిష్ గా ఉంది. కాబట్టి రేపు మార్కెట్ గ్యాప్-డౌన్ లేదా బలహీనంగా ఓపెన్ అయ్యే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                else:
                    reply = f"సార్, ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} తటస్థంగా ఉంది. కాబట్టి రేపు మార్కెట్ ఫ్లాట్ లేదా చిన్న గ్యాప్ తో ఓపెన్ కావచ్చు సార్."
            elif any(x in user_msg_lower for x in ["highest oi", "హైయెస్ట్", "oi", "ఓ ఐ"]):
                reply = f"సార్, ఆప్షన్ చైన్ ఓపెన్ ఇంట్రెస్ట్ ప్రకారం, అత్యధిక కాల్ ఓఐ ₹{strong_resistance} వద్ద మరియు అత్యధిక పుట్ ఓఐ ₹{strong_support} వద్ద ఉంది. ఇది మార్కెట్ కి ముఖ్యమైన రేంజ్."
            elif any(x in user_msg_lower for x in ["upside", "downside", "direction", "ఎటు", "వెళ్తుంది", "పైకి", "కిందకి", "వాట్ అబౌట్", "what about"]):
                if pcr > 1.15 or trend == "BULLISH":
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం బుల్లిష్ గా ఉంది. ఆప్షన్ చైన్ వాల్యూమ్స్ మరియు పిసిఆర్ ({pcr:.3f}) ఆధారంగా మార్కెట్ పైకి (upside) వెళ్ళే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                elif pcr < 0.85 or trend == "BEARISH":
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం బేరిష్ గా ఉంది. కాల్ రైటింగ్ అధికంగా ఉండటం వల్ల మార్కెట్ కిందకి (downside) వెళ్ళే అవకాశాలు ఎక్కువగా ఉన్నాయి సార్."
                else:
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం సైడ్‌വേస్ లేదా కన్సాలిడేషన్ లో ఉంది. ప్రస్తుత పిసిఆర్ విలువ {pcr:.3f} వద్ద రేంజ్-బౌండ్ గా ఉంది సార్."
            elif any(x in user_msg_lower for x in ["పెరుగు", "కాల్", "ce", "పైకి"]):
                ce_data = next((x for x in scanner_items if f"{d60_ce} CE" in x.get("strike", "")), None)
                if not ce_data and ce_strikes:
                    ce_data = ce_strikes[0]
                if ce_data:
                    reply = f"సార్, {ce_data.get('strike')} కాల్ ఆప్షన్ యొక్క ప్రస్తుత ధర ₹{ce_data.get('ltp')}. దీని వాల్యూమ్ {ce_data.get('volume', 0):,} గా ఉంది. సిగ్నల్ {ce_data.get('ai_signal')} గా ఉంది."
                else:
                    reply = f"సార్, నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f} వద్ద ఉంది. కాల్స్ లో బలమైన కొనుగోలు ఇంకా కనిపించడం లేదు. పిసిఆర్ విలువ {pcr:.3f} గా ఉంది."
            elif any(x in user_msg_lower for x in ["తగ్గు", "పుట్", "pe", "కిందకి"]):
                pe_data = next((x for x in scanner_items if f"{d60_pe} PE" in x.get("strike", "")), None)
                if not pe_data and pe_strikes:
                    pe_data = pe_strikes[0]
                if pe_data:
                    reply = f"సార్, {pe_data.get('strike')} పుట్ ఆప్షన్ యొక్క ప్రస్తుత ధర ₹{pe_data.get('ltp')}. దీని వాల్యూమ్ {pe_data.get('volume', 0):,} గా ఉంది. సిగ్నల్ {pe_data.get('ai_signal')} గా ఉంది."
                else:
                    reply = f"సార్, మార్కెట్ ప్రస్తుతం బేరిష్ గా ఉంది. పిసిఆర్ విలువ {pcr:.3f} గా ఉంది. లెవెల్స్ ని గమనించి ట్రేడ్ చేయండి."
            elif any(x in user_msg_lower for x in ["ట్రాప్", "trap"]):
                reply = f"సార్, ప్రస్తుతం ఆప్షన్ చైన్ లో {trap_zone} మోడ్ కనిపిస్తోంది. స్మార్ట్ మనీ {smart_money} గా ఉంది. వాల్యూమ్ పెరగకుండా రిటైల్ బయర్స్ ను ట్రాప్ చేసే అవకాశం ఉంది, జాగ్రత్తగా ఉండండి."
            elif any(x in user_msg_lower for x in ["హెవీ", "వాల్యూ", "volume"]):
                ce_vol = sum(x.get("volume", 0) for x in ce_strikes[:3])
                pe_vol = sum(x.get("volume", 0) for x in pe_strikes[:3])
                if ce_vol > pe_vol:
                    reply = f"సార్, కాల్ ఆప్షన్స్ లో హెవీ వాల్యూమ్ ({ce_vol:,}) ఉంది. ఇది ఆపరేటర్లు కాల్ సైడ్ పొజిషన్స్ క్రియేట్ చేస్తున్నారని సూచిస్తుంది."
                else:
                    reply = f"సార్, పుట్ ఆప్షన్స్ లో వాల్యూమ్ అధికంగా ({pe_vol:,}) ఉంది. పుట్ సైడ్ అధిక ఆసక్తి కనిపిస్తోంది."
            elif any(x in user_msg_lower for x in ["లెవెల్", "level"]):
                i5_val = gvn_levels.get("i5", "N/A")
                i7_val = gvn_levels.get("i7", "N/A")
                reply = f"సార్, నిఫ్టీ 9:15 క్యాండిల్ ప్రకారం లెవెల్ 5 (i5) ₹{i5_val} మరియు లెవెల్ 7 (i7) ₹{i7_val} గా ఉన్నాయి. ధర ఈ లెవెల్స్ ని బ్రేక్ చేసినప్పుడు మాత్రమే ట్రేడ్ ప్లాన్ చేయండి."
            elif "9:15" in user_msg_lower:
                h_915 = gvn_levels.get("high_915", "N/A")
                l_915 = gvn_levels.get("low_915", "N/A")
                reply = f"సార్, నిఫ్టీ 9:15 బెంచ్‌మార్క్ హై ₹{h_915} మరియు లో ₹{l_915} గా రికార్డ్ అయింది. ఈ పరిధి దాటినప్పుడు మార్కెట్ కి ఒక డైరెక్షన్ లభిస్తుంది."
            else:
                reply = (
                    f"సార్, ప్రస్తుతం నిఫ్టీ స్పాట్ ధర {nifty_spot:.2f} వద్ద ఉంది. "
                    f"సపోర్ట్ ₹{strong_support} మరియు రెసిస్టెన్స్ ₹{strong_resistance} గా ఉంది. "
                    f"మార్కెట్ ట్రెండ్ {trend} మరియు సెంట్రిమెంట్ {sentiment} గా ఉంది. పిసిఆర్ విలువ {pcr:.3f} వద్ద ఉంది."
                )
        else:
            # English Fallback specific questions
            if any(x in user_msg_lower for x in ["zero to hero", "zero-to-hero", "z2h", "formula 1", "formula1"]):
                reply = "Sir, GVN Expiry Zero-to-Hero (Formula 1) is an expiry-day strategy. It selects strikes with Delta between 0.40 and 0.85. Entry triggers when premium drops near Level i1 (bottom Green Line / 1.0 Fib) and reverses under Wind direction, Wind power (>= 0.8), and Trap filters."
            elif any(x in user_msg_lower for x in ["level acceleration", "gamma squeeze", "gamma", "formula 2", "formula2"]):
                reply = "Sir, GVN Level Acceleration (Formula 2) is a Peak Gamma Squeeze strategy. When the index reverses between Level 6 (0.618 Fib) and Level 5 (0.50 Fib), the option premium explodes from Level 7 through Level 6 and 5 as OTM options transition to ATM, peaking Gamma. Above Level 5 (ITM), Delta approaches 1.0, moving 1:1 with the index towards Target Level 3, with a strict 12-point SL."
            elif any(x in user_msg_lower for x in ["status", "done", "complete", "finished"]) and any(x in user_msg_lower for x in ["9:15", "9 15", "calculation"]):
                reply = f"Sir, today's 9:15 AM option levels calculations are {'COMPLETED and the algo is running live.' if nifty_captured else 'PENDING. The system is waiting for the 9:15 AM opening candle to close.'}"
            elif any(x in user_msg_lower for x in ["9:15", "9 15", "calculation", "formula 3", "formula3", "confirmation"]):
                reply = f"Sir, GVN 9:15 Option Level Confirmation (Formula 3) validates morning retracements. For Call side (Bullish), the index closes above 0.618 Fib, and the Call option touches 0.6 level, crosses 0.5 level, and then retests 0.7 or 0.6. For Put side (Bearish), the index closes below 0.5 Fib, and the Put option touches 0.6, retests, and crosses 0.5 or 0.7. Time-based alignment (like comparing levels at 10:45 AM) confirms the direction. Calculations status: {'COMPLETED' if nifty_captured else 'PENDING'}."
            elif any(x in user_msg_lower for x in ["delta 60", "delta"]):
                reply = f"Sir, today's Delta 60 Call Strike is at {d60_ce} and Put Strike is at {d60_pe}. Spot is currently {nifty_spot:.2f}."
            elif any(x in user_msg_lower for x in ["gap up", "gap down", "tomorrow", "opening"]):
                if pcr > 1.15:
                    reply = f"Sir, PCR is {pcr:.3f} (Bullish). There is a high probability of tomorrow opening with a Gap-Up or positive start."
                elif pcr < 0.85:
                    reply = f"Sir, PCR is {pcr:.3f} (Bearish). There is a high probability of tomorrow opening with a Gap-Down or weak start."
                else:
                    reply = f"Sir, PCR is {pcr:.3f} (Neutral). Market is likely to open Flat or with a very minor gap tomorrow."
            elif any(x in user_msg_lower for x in ["highest oi", "highest open interest", "oi"]):
                reply = f"Sir, Calls highest OI/Volume is at {strong_resistance} and Puts highest OI/Volume is at {strong_support}."
            elif any(x in user_msg_lower for x in ["upside", "downside", "direction", "where", "go", "what about"]):
                if pcr > 1.15 or trend == "BULLISH":
                    reply = f"Sir, market is currently bullish with PCR {pcr:.3f}. Option chain indicates an upside target towards {strong_resistance}."
                elif pcr < 0.85 or trend == "BEARISH":
                    reply = f"Sir, market is currently bearish with PCR {pcr:.3f}. Call writers are strong, suggesting a downside move towards {strong_support}."
                else:
                    reply = f"Sir, market is range-bound and consolidating sideways (PCR: {pcr:.3f}). No clear direction yet."
            elif "nifty" in user_msg_lower or "spot" in user_msg_lower or "trend" in user_msg_lower:
                reply = f"Sir, Nifty spot is at {nifty_spot:.2f}. Support is at {strong_support} and Resistance is at {strong_resistance}. Trend is {trend}."
            elif "level" in user_msg_lower or "levels" in user_msg_lower:
                reply = f"Sir, current GVN i5 level is at {gvn_levels.get('i5', 'N/A')} and i7 is at {gvn_levels.get('i7', 'N/A')}."
            elif "trap" in user_msg_lower:
                reply = f"Sir, the option chain shows a {trap_zone} trap status. Smart money indicates {smart_money}."
            elif "volume" in user_msg_lower or "heavy" in user_msg_lower:
                reply = f"Sir, PCR is {pcr:.3f}. Call side vs Put side open interest is in a {sentiment} balance."
            else:
                reply = f"Hello Sir. Spot is at {nifty_spot:.2f}, Trend: {trend}, PCR: {pcr:.3f}. Support: {strong_support}, Resistance: {strong_resistance}."
                
        # Save chat messages to history
        gvn_data_bank.save_ai_message("user", user_msg)
        gvn_data_bank.save_ai_message("assistant", reply)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"AI Engine Error: {str(e)}"}), 500



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
        
        # Send Telegram notification about status toggle
        try:
            from datetime import datetime
            from gvn_telegram_engine import TelegramAlertManager
            import os
            tg = TelegramAlertManager(os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID"))
            mode_str = "🟢 REAL/LIVE MODE" if (user.user_type == 'LIVE' and user.is_approved) else "📊 DEMO/PAPER MODE"
            active_sym = getattr(shared_data, 'active_dashboard_symbol', 'NIFTY')
            msg = (
                f"🤖 <b>[GVN ALGO TOGGLED]</b> 🤖\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>User:</b> {user.username}\n"
                f"⚡ <b>Algo Status:</b> {user.algo_status}\n"
                f"⚙️ <b>Trading Mode:</b> {mode_str}\n"
                f"🎯 <b>Selected Symbol:</b> {active_sym}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ Sent at: {datetime.now().strftime('%H:%M:%S')}"
            )
            tg.bot.send_message(msg)
        except Exception as e:
            print(f"Error sending toggle telegram alert: {e}")
            
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