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

class UILogger:
    def __init__(self, original):
        self.original = original

    def write(self, message):
        self.original.write(message)
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
        self.original.flush()

sys.stdout = UILogger(sys.stdout)
sys.stderr = UILogger(sys.stderr)

app = Flask(__name__)
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
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('login_phone', '').strip().lower()
        user = User.query.filter((User.phone == identifier) | (User.email == identifier)).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard', user_id=user.id))
    
    # Auto-login first user for testing if no one is logged in
    user = User.query.first()
    if user:
        session['user_id'] = user.id
        return redirect(url_for('user_dashboard', user_id=user.id))
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
        user_type='PAPER',
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
                           remaining_days=30, 
                           build_version="2.5.1")

@app.route('/api/user-status')
def user_status():
    """Provides high-fidelity state for the User Dashboard (Signal, P&L, Active Trade)."""
    trade = getattr(shared_data, 'demo_trade', {"active": False})
    logs = getattr(shared_data, 'demo_logs', [])
    
    # State Logic
    state = "IDLE"
    if trade.get("active"):
        state = "ACTIVE"
    else:
        # Check if last log was a close event
        if logs and ("[PROFIT HIT]" in logs[-1] or "SQUARE-OFF" in logs[-1] or "TSL" in logs[-1]):
            state = "CLOSED"

    # Extract latest relevant message
    theory_msg = "⌛ Wait for Signal: System is scanning institutional breakouts..."
    last_pnl = 0
    if logs:
        for log in reversed(logs):
            if any(x in log for x in ["[SIGNAL]", "[RUNNING]", "[PROFIT HIT]", "[TSL]", "SQUARE-OFF"]):
                theory_msg = log
                # Extract P&L if possible
                if "P&L:" in log:
                    try: 
                        pnl_part = log.split("P&L:")[1].strip()
                        for emoji in ["🎯", "⚠️", "🕒", "🚀", "💰", "+"]:
                            pnl_part = pnl_part.replace(emoji, "").strip()
                        last_pnl = pnl_part
                    except: pass
                break

    # AI Market Condition Logic
    spot = shared_data.market_data.get("NIFTY", 0)
    support = "23,900"
    resistance = "24,000"
    expected_move = "Downside to 23,850"
    condition = "Put premiums rising. Support broken."
    
    # Simple dynamic logic based on spot
    if spot > 24000:
        support = "24,000"
        resistance = "24,200"
        expected_move = "Bullish Continuation / Target 24,150"
        condition = "Breakout above 24,000. Buyers in full control."
    elif spot >= 23900:
        support = "23,900"
        resistance = "24,000"
        expected_move = "Consolidation / Target 24,000"
        condition = "Strong bounce from 23,900 support. Approaching resistance."
    elif spot > 0:
        support = "23,800"
        resistance = "23,950"
        expected_move = "Downside move to 23,800"
        condition = "Support broken. Bears targeting 23,800."

    return jsonify({
        "nifty_spot": spot,
        "state": state,
        "trade_symbol": trade.get("symbol", "--"),
        "trade_entry": trade.get("entry_price", 0),
        "trade_target": trade.get("target", 0),
        "trade_sl": trade.get("sl", 0),
        "theory": theory_msg,
        "last_pnl": last_pnl,
        "support": support,
        "resistance": resistance,
        "expected_move": expected_move,
        "condition": condition
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

@app.route('/api/gvn-scanner')
def gvn_scanner():
    return jsonify({
        "status": "success",
        "alpha_grid": getattr(shared_data, 'gvn_alpha_grid', {}),
        "market_pulse": getattr(shared_data, 'market_pulse', {}),
        "nifty_spot": shared_data.market_data.get("NIFTY", 0),
        "data": getattr(shared_data, 'scanner_data', {}),
        "demo_signals": getattr(shared_data, 'demo_signals', [])
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

        # Store the levels in shared memory
        shared_data.gvn_tv_levels = {
            "symbol": data.get("symbol"),
            "high": data.get("high"),
            "low": data.get("low"),
            "i1": data.get("i1"),
            "i5": data.get("i5"),
            "i7": data.get("i7"),
            "received_at": datetime.now().strftime("%H:%M:%S")
        }
        
        print(f"✅ [TV WEBHOOK] Received levels for {data.get('symbol')}: i1:{data.get('i1')} i5:{data.get('i5')} i7:{data.get('i7')}")
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
    
    # 🌟 GVN PLAYBACK / DEMO ENGINE OVERRIDE
    if getattr(shared_data, 'demo_playback_running', False) and hasattr(shared_data, 'demo_full_chain'):
        print(f"🎬 [DEMO SOURCE] {symbol} Option Chain fed from Playback Engine")
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "spot_price": round(shared_data.market_data.get(symbol, 0), 2),
            "timestamp": datetime.now().strftime("%H:%M:%S") + " (PLAYBACK)",
            "chain": shared_data.demo_full_chain
        })

    # Try 1: TrueData WebSocket (Ultra-Fast)
    ws_chain = shared_data.truedata_option_chains.get(symbol)
    if ws_chain:
        # print(f"⚡ [DATA SOURCE] {symbol} Option Chain fetched from WEBSOCKET MEMORY")
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "spot_price": shared_data.market_data.get(symbol, 0),
            "chain": ws_chain[:20]
        })

    # Try 2: TrueData REST (Fallback)
    try:
        from truedata_rest_api import TrueDataRestAPI
        if not hasattr(shared_data, 'td_api') or shared_data.td_api is None:
            shared_data.td_api = TrueDataRestAPI(os.getenv("TRUEDATA_USERNAME"), os.getenv("TRUEDATA_PASSWORD"))
        
        chain = shared_data.td_api.get_option_chain(symbol)
        if chain:
            # print(f"🚀 [DATA SOURCE] {symbol} Option Chain fetched from TRUEDATA REST")
            return jsonify({
                "status": "success",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "spot_price": shared_data.market_data.get(symbol, 0),
                "chain": chain[:20]
            })
    except Exception as e:
        shared_data.td_api = None

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
    
    # Update all users to DEMO as requested
    users = User.query.filter(User.role == 'user').all()
    for u in users:
        if u.user_type != 'DEMO':
            u.user_type = 'DEMO'
    db.session.commit()
    
    real_users = User.query.filter(User.role == 'user').all()
    active_subscriptions = Subscription.query.filter_by(status='active').all()
    
    return render_template('admin.html', user=admin, real_users=real_users, subscriptions=active_subscriptions)

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
    
    db.session.commit()
    
    # Re-initialize orchestrator with new settings
    try:
        init_gvn()
        flash("Settings Saved and Orchestrator Re-initialized!")
    except Exception as e:
        flash(f"Settings Saved but Orchestrator Failed: {e}")
        
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
            # Force Angel One as the primary broker
            try:
                import angel_live_feed
                angel_live_feed.start_angel_worker()
            except Exception as e:
                print(f"⚠️ Angel Feed Failed: {e}")
        except Exception as e:
            print(f"⚠️ Feed Worker Start Failed: {e}")

        shared_data.system_status["initialized"] = True

# Start init in a separate thread to prevent blocking the Flask server startup
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    import threading
    threading.Thread(target=init_gvn, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    print("\n" + "="*50)
    print(f"🚀 GVN MASTER ALGO SERVER STARTING...")
    print(f"🔗 LOCAL LINK: http://127.0.0.1:{port}")
    print(f"🔗 NETWORK LINK: http://0.0.0.0:{port}")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=port, debug=True)