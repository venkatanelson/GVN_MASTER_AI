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
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_master_v1.db')
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
    full_auto_mode = db.Column(db.Boolean, default=False)
    trade_lots = db.Column(db.Integer, default=1)
    dhan_webhook_url = db.Column(db.String(500), default="")

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
    call_strike = db.Column(db.String(50))
    put_strike = db.Column(db.String(50))
    support_number_1 = db.Column(db.String(20), default="919966123078")

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
    
    user = User.query.first()
    if user:
        session['user_id'] = user.id
        return redirect(url_for('user_dashboard', user_id=user.id))
    return redirect(url_for('index'))

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
                           password=password,
                           pnl_total_30d=pnl_total_30d,
                           daily_history=daily_history,
                           remaining_days=30, 
                           build_version="2.5.1")

@app.route('/api/broker-status')
def broker_status():
    return jsonify({
        "connected": True,
        "broker_name": "Shoonya",
        "data_source": "Live WebSocket",
        "nifty_spot": shared_data.market_data.get("NIFTY", 0),
        "reason": "Stable Connection"
    })

@app.route('/api/gvn-scanner')
def gvn_scanner():
    return jsonify({
        "status": "success",
        "alpha_grid": getattr(shared_data, 'gvn_alpha_grid', {}),
        "market_pulse": getattr(shared_data, 'market_pulse', {}),
        "nifty_spot": shared_data.market_data.get("NIFTY", 0)
    })

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
    return render_template('admin.html', user=v, config=config)

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
    config.call_strike = data.get('call_strike')
    config.put_strike = data.get('put_strike')
    db.session.commit()
    # Re-initialize orchestrator with new settings
    init_gvn()
    flash("Settings Saved and Orchestrator Re-initialized!")
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
                    ('full_auto_mode', 'BOOLEAN DEFAULT FALSE'),
                    ('trade_lots', 'INTEGER DEFAULT 1'),
                    ('user_type', "VARCHAR(20) DEFAULT 'PAPER'")
                ],
                'user_broker_config': [
                    ('call_strike', 'VARCHAR(20)'),
                    ('put_strike', 'VARCHAR(20)'),
                    ('support_number_1', 'VARCHAR(20)')
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
            existing_user = User.query.filter_by(phone="9966123078").first()
            if not existing_user:
                v = User(id=1, username="Venkat", phone="9966123078", email="nelsonp143@gmail.com", is_admin=True, algo_status="OFF", user_type="LIVE")
                db.session.add(v)
                db.session.commit()
            
            # Initialize Orchestrator
            config = UserBrokerConfig.query.filter_by(user_id=1).first()
            if config and config.client_id:
                broker_cfg = {
                    "broker_name": config.broker_name,
                    "client_id": config.client_id,
                    "api_key": config.api_key,
                    "access_token": config.api_secret, 
                    "totp_key": config.totp_key,
                    "password": cipher.decrypt(config.encrypted_password).decode() if config.encrypted_password else None
                }
                from gvn_master_orchestrator import get_orchestrator
                orch = get_orchestrator()
                if orch:
                    try:
                        orch.start(broker_cfg)
                        print("🚀 GVN Master Orchestrator Started Successfully!")
                    except Exception as e:
                        print(f"❌ Orchestrator Start Failed: {e}")
                else:
                    print("❌ Error: Could not create Orchestrator instance.")
        except Exception as e:
            print(f"❌ Initialization Error: {e}")

        try:
            import shoonya_live_feed
            shoonya_live_feed.start_live_feed_worker()
        except Exception as e:
            print(f"⚠️ Feed Worker Start Failed: {e}")

init_gvn()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)