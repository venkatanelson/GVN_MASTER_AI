import os
import base64
import requests
import concurrent.futures
from functools import wraps
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

app = Flask(__name__)

# Basic app config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_flask_key_2026')

# 🌟 NEW: Neon PostgreSQL Database URL
# If DATABASE_URL is in the environment (e.g., Render/Neon), use Postgres. Otherwise, use local SQLite.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
# Quick fix for Render & SQLAlchemy (replace postgres:// with postgresql://)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db = SQLAlchemy(app)

# Encryption Key
static_32_byte_string = b'gvn_secure_key_for_encryption_26'
fallback_key = base64.urlsafe_b64encode(static_32_byte_string)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', fallback_key)
cipher = Fernet(ENCRYPTION_KEY)

# Admin Authentication
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
        'Admin access required.\n'
        'Could not verify your access level.\n'
        'Login required (Default: admin / admin123)', 401,
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

class TradeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    signal_message = db.Column(db.String(500))
    pnl = db.Column(db.Float, default=0.0) # 🌟 P&L రికార్డ్
    status = db.Column(db.String(50), default="Processed")

# ---------------------------------------------------------
# REGISTRATION & ROUTES
# ---------------------------------------------------------

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('demo_register'))

@app.route('/demo-register', methods=['GET', 'POST'])
def demo_register():
    if request.method == 'POST':
        username = request.form.get('username')
        phone = request.form.get('phone')
        email = request.form.get('email')
        capital = int(request.form.get('demo_capital', 50000))
        
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
            is_approved=True, # Auto approve demos usually
            expiry_date=datetime.now() + timedelta(days=7), # 7 days demo
            algo_status='ON'
        )
        db.session.add(new_user)
        try:
            db.session.commit()
            return redirect(url_for('user_dashboard', user_id=new_user.id))
        except:
            db.session.rollback()
            return "Email or Phone already exists!"
            
    return """
    <h2>Demo Registration</h2>
    <form method="POST">
        <input type="text" name="username" placeholder="Name" required><br>
        <input type="text" name="phone" placeholder="Phone" required><br>
        <input type="email" name="email" placeholder="Email" required><br>
        <label>Demo Capital (₹50k - ₹1Lakh):</label><br>
        <input type="number" name="demo_capital" min="50000" max="100000" value="50000" required><br><br>
        <button type="submit">Start Demo Trading</button>
    </form>
    """

# 🌟 USER DASHBOARD ROUTE (With Specific PnL Logic)
@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    now = datetime.now()
    remaining_days = (user.expiry_date - now).days if user.expiry_date else 0
    
    # --- Calculate Dynamic P&L ---
    total_trades = TradeHistory.query.all()
    
    pnl_1d = 0
    pnl_10d = 0
    pnl_20d = 0
    pnl_30d = 0
    
    for t in total_trades:
        days_diff = (now - t.timestamp).days
        if days_diff <= 1: pnl_1d += t.pnl
        if days_diff <= 10: pnl_10d += t.pnl
        if days_diff <= 20: pnl_20d += t.pnl
        if days_diff <= 30: pnl_30d += t.pnl
    
    return render_template('user.html', 
                           user=user, 
                           remaining_days=max(0, remaining_days),
                           discount_percent=user.personal_discount + 10, # Base 10 + personal
                           pnl_1d=pnl_1d,
                           pnl_10d=pnl_10d,
                           pnl_20d=pnl_20d,
                           pnl_30d=pnl_30d)


# ---------------------------------------------------------
# TRADING LOGIC (The Mechanism)
# ---------------------------------------------------------

@app.route('/tv-webhook', methods=['POST'])
def handle_tradingview_alert():
    alert_data = request.json # TradingView Message
    signal_msg = alert_data.get("message", "TV Signal Received")
    
    try:
        pnl_value = float(alert_data.get("pnl", 0.0))
    except (TypeError, ValueError):
        pnl_value = 0.0

    # 1. Record in History (Viewable by everyone)
    new_trade = TradeHistory(signal_message=signal_msg, pnl=pnl_value, timestamp=datetime.now())
    db.session.add(new_trade)
    db.session.commit()
    
    # 2. Filter REAL Users
    real_active_users = User.query.filter_by(user_type='REAL', is_approved=True, algo_status='ON', admin_kill_switch=False).all()
    
    def execute_trade(u):
        with app.app_context():
            if u.expiry_date and u.expiry_date > datetime.now():
                try:
                    if not u.encrypted_secret_key or not u.dhan_webhook_url:
                        return
                        
                    secret_key = cipher.decrypt(u.encrypted_secret_key).decode()
                    dhan_payload = {"secret": secret_key, "alert_msg": signal_msg}
                    
                    response = requests.post(u.dhan_webhook_url, json=dhan_payload, timeout=5)
                except Exception as e:
                    print(f"Trade Exception for {u.username}: {e}")
            else:
                expired_user = User.query.get(u.id)
                expired_user.algo_status = 'OFF'
                db.session.commit()

    # 3. Use Multi-threading ONLY for Real Users (Demo users just see history)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(execute_trade, real_active_users)
            
    return jsonify({"status": "Signals Processed & Saved", "real_trades_fired": len(real_active_users)}), 200

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
                           g_discount=10)

@app.route('/approve-user/<int:user_id>/<int:months>')
@requires_auth
def approve_user(user_id, months):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    user.expiry_date = datetime.now() + timedelta(days=30 * months)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/toggle-kill-switch/<int:user_id>')
@requires_auth
def toggle_kill_switch(user_id):
    user = User.query.get_or_404(user_id)
    user.admin_kill_switch = not user.admin_kill_switch
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/history')
def trade_history():
    history = TradeHistory.query.order_by(TradeHistory.timestamp.desc()).limit(1000).all()
    total_pnl = sum((t.pnl for t in history if t.pnl))
    return render_template('history.html', trades=history, total_pnl=total_pnl)

@app.route('/clear-history')
@requires_auth
def clear_history():
    db.session.query(TradeHistory).delete()
    db.session.commit()
    return redirect(url_for('trade_history'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
