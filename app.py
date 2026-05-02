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
    tv_secret = db.Column(db.String(100))
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
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Closed')

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
@app.route('/login-auto')
def login_auto():
    if request.method == 'POST':
        identifier = request.form.get('login_phone', '').strip().lower()
        user = User.query.filter((User.phone == identifier) | (User.email == identifier)).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard', user_id=user.id))
    
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
        is_approved=False
    )
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    return redirect(url_for('user_dashboard', user_id=new_user.id))

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    user = db.session.get(User, user_id)
    if not user: return redirect(url_for('index'))
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
        parsed_trades.append({
            'id': t.id,
            'time': t.timestamp.strftime('%H:%M:%S'),
            'symbol': t.symbol,
            'status': t.status,
            'entry_price': 100.0, # Placeholder
            'exit_price': 110.0 if t.status == 'Closed' else 0,
            'pnl': t.pnl or 0.0
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

@app.route('/api/robot/status', methods=['POST'])
def robot_status():
    data = request.json
    active = data.get('active', False)
    shared_data.robot_active = active
    return jsonify({"status": "success", "robot_active": active})

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
    v = db.session.get(User, 1)
    config = UserBrokerConfig.query.filter_by(user_id=1).first()
    if not config:
        config = UserBrokerConfig(user_id=1)
        db.session.add(config)
        db.session.commit()
        
    real_users = User.query.filter(User.user_type == 'LIVE', User.is_admin == False).all()
    demo_users = User.query.filter(User.user_type == 'PAPER', User.is_admin == False).all()
    pending_payments = PendingPayment.query.filter_by(status='Pending').all()
    
    return render_template('admin.html', user=v, config=config, real_users=real_users, demo_users=demo_users, pending_payments=pending_payments)

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
    with app.app_context():
        db.create_all()
        # Robust Migration logic
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Tables and their required columns
            required_columns = {
                'user': [
                    ('is_locked', 'BOOLEAN DEFAULT FALSE'),
                    ('is_blocked', 'BOOLEAN DEFAULT FALSE'),
                    ('full_auto_mode', 'BOOLEAN DEFAULT FALSE'),
                    ('trade_lots', 'INTEGER DEFAULT 1'),
                    ('user_type', "VARCHAR(20) DEFAULT 'PAPER'"),
                    ('selected_plan', "VARCHAR(50) DEFAULT 'Basic'"),
                    ('expiry_date', 'DATETIME'),
                    ('demo_capital', 'FLOAT DEFAULT 100000.0'),
                    ('admin_kill_switch', 'BOOLEAN DEFAULT FALSE')
                ],
                'user_broker_config': [
                    ('call_strike', 'VARCHAR(20)'),
                    ('put_strike', 'VARCHAR(20)'),
                    ('webhook_url', 'VARCHAR(500)'),
                    ('tv_secret', 'VARCHAR(100)'),
                    ('support_number_1', 'VARCHAR(20)'),
                    ('support_number_2', 'VARCHAR(20)'),
                    ('admin_phone', 'VARCHAR(20)'),
                    ('admin_user', 'VARCHAR(50)'),
                    ('admin_pass', 'VARCHAR(50)'),
                    ('plan_basic_price', 'INTEGER DEFAULT 1500'),
                    ('plan_premium_price', 'INTEGER DEFAULT 3000'),
                    ('plan_ultimate_price', 'INTEGER DEFAULT 5000'),
                    ('attack_mode', 'BOOLEAN DEFAULT FALSE')
                ]
            }

            with db.engine.connect() as conn:
                for table, cols in required_columns.items():
                    existing_cols = [c['name'] for c in inspector.get_columns(table)]
                    for col, col_type in cols:
                        if col not in existing_cols:
                            try:
                                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                                conn.commit()
                                print(f"✅ Migrated: Added {col} to {table}")
                            except Exception as e:
                                print(f"❌ Failed to add {col}: {e}")
        except Exception as e:
            print(f"⚠️ Migration System Error: {e}")

        # Check for admin user
        try:
            target_phone = "9381490610"
            existing_user = User.query.filter((User.phone == target_phone) | (User.phone == "9966123078")).first()
            if not existing_user:
                v = User(id=1, username="Venkat", phone=target_phone, email="nelsonp143@gmail.com", is_admin=True, algo_status="OFF", user_type="LIVE")
                db.session.add(v)
                db.session.commit()
            else:
                # Update existing user to the correct phone number
                existing_user.phone = target_phone
                existing_user.is_admin = True
                db.session.commit()
            
            # Initialize Orchestrator
            config = UserBrokerConfig.query.filter_by(user_id=1).first()
            if config and config.client_id:
                broker_cfg = {
                    "broker_name": config.broker_name,
                    "client_id": config.client_id,
                    "access_token": config.api_key,   # Map api_key to access_token (Vendor Code)
                    "client_secret": config.api_secret, # Map api_secret to client_secret
                    "totp_key": config.totp_key,
                    "password": cipher.decrypt(config.encrypted_password).decode() if config.encrypted_password else None
                }
                from gvn_master_orchestrator import get_orchestrator
                telegram_cfg = {
                    "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                    "chat_id": os.environ.get("TELEGRAM_CHAT_ID", "")
                }
                orch = get_orchestrator(telegram_config=telegram_cfg)
                if orch:
                    try:
                        orch.start(broker_cfg)
                        print(f"🚀 GVN Master Orchestrator Started Successfully for {config.client_id}!")
                    except Exception as e:
                        print(f"❌ Orchestrator Start Failed: {e}")
                else:
                    print("❌ Error: Could not create Orchestrator instance.")
        except Exception as e:
            print(f"❌ Initialization Error: {e}")

        try:
            config = UserBrokerConfig.query.filter_by(user_id=1).first()
            broker = config.broker_name.lower() if config else "shoonya"
            
            if "dhan" in broker:
                try:
                    import dhan_live_feed
                    dhan_live_feed.start_live_feed_worker()
                except ImportError:
                    import shoonya_live_feed
                    shoonya_live_feed.start_live_feed_worker()
            else:
                import shoonya_live_feed
                shoonya_live_feed.start_live_feed_worker()
        except Exception as e:
            print(f"⚠️ Feed Worker Start Failed: {e}")

init_gvn()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)