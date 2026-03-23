import os
import base64
import requests
import concurrent.futures
from functools import wraps
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, Response, session
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
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=5, minutes=30))
    signal_message = db.Column(db.String(500))
    pnl = db.Column(db.Float, default=0.0) # 🌟 P&L రికార్డ్
    status = db.Column(db.String(50), default="Processed")

class DailyPnL(db.Model):
    __tablename__ = 'daily_pnl_tracker'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    pnl = db.Column(db.Float, default=0.0)

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
            expiry_date=datetime.now() + timedelta(days=7),
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
            # If database raised unique constraint error despite our prior check (e.g., casing issues previously saved)
            fallback = User.query.filter((User.email.ilike(email)) | (User.phone == phone)).first()
            if fallback:
                session.permanent = True
                session['user_id'] = fallback.id
                return redirect(url_for('user_dashboard', user_id=fallback.id))
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

@app.route('/plans')
def subscription_plans():
    return render_template('plans.html')

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
    start_of_today = datetime(today_date.year, today_date.month, today_date.day)
    TradeHistory.query.filter(TradeHistory.timestamp < start_of_today).delete()
    db.session.commit()
    
    # Parse today's trades for the live historical table dynamically (NO SCHEMA CHANGES!)
    todays_trades = TradeHistory.query.order_by(TradeHistory.timestamp.desc()).all()
    parsed_trades = []
    import re
    for t in todays_trades:
        sm = str(t.signal_message).upper()
        sym = re.split(r'BUY|SELL|TARGET|SL|STOPLOSS', sm)[0].strip() if sm else "ALGO"
        
        t_type = "SIGNAL"
        if "BUY" in sm: t_type = "BUY"
        elif "SELL" in sm: t_type = "SELL"
        
        res = "Running"
        if "TARGET" in sm or "HIT" in sm: res = "Target Hit"
        elif "SL" in sm or "STOPLOSS" in sm or "EXIT" in sm: res = "SL Hit"
        
        parsed_trades.append({
            "time": t.timestamp.strftime('%H:%M:%S'),
            "symbol": sym[:20],
            "type": t_type,
            "result": res,
            "pnl": t.pnl
        })
        
    # --- Calculate Dynamic Cumulative P&L ---
    all_daily = DailyPnL.query.filter(DailyPnL.date >= (today_date - timedelta(days=30))).all()
    date_to_pnl = {dp.date: dp.pnl for dp in all_daily}
    
    pnl_1d = sum(t.pnl for t in todays_trades)
    
    # Sync today's Live P&L to database so it stays permanently
    today_record = DailyPnL.query.filter_by(date=today_date).first()
    if not today_record:
        db.session.add(DailyPnL(date=today_date, pnl=pnl_1d))
    else:
        today_record.pnl = pnl_1d
    try: db.session.commit()
    except: db.session.rollback()
    
    # Cumulative Sums (10, 20, 30 Days over all records)
    pnl_10d = pnl_1d + sum(date_to_pnl.get(today_date - timedelta(days=i), 0.0) for i in range(1, 10))
    pnl_20d = pnl_1d + sum(date_to_pnl.get(today_date - timedelta(days=i), 0.0) for i in range(1, 20))
    pnl_30d = pnl_1d + sum(date_to_pnl.get(today_date - timedelta(days=i), 0.0) for i in range(1, 30))
    
    return render_template('user.html', 
                           user=user, 
                           remaining_days=max(0, remaining_days),
                           discount_percent=user.personal_discount + 10, # Base 10 + personal
                           pnl_1d=pnl_1d,
                           pnl_10d=pnl_10d,
                           pnl_20d=pnl_20d,
                           pnl_30d=pnl_30d,
                           parsed_trades=parsed_trades)


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
    today_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
    new_trade = TradeHistory(signal_message=signal_msg, pnl=pnl_value, timestamp=today_dt)
    db.session.add(new_trade)
    
    daily_record = DailyPnL.query.filter_by(date=today_dt.date()).first()
    if not daily_record:
        db.session.add(DailyPnL(date=today_dt.date(), pnl=pnl_value))
    else:
        daily_record.pnl = DailyPnL.pnl + pnl_value
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

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    user_id = int(request.form.get('user_id', 0))
    if not user_id:
        return "Invalid User", 400
        
    webhook_url = request.form.get('webhook_url')
    secret_key = request.form.get('secret_key')
    
    user = User.query.get_or_404(user_id)
    user.dhan_webhook_url = webhook_url
    if secret_key and secret_key != '********':
        user.encrypted_secret_key = cipher.encrypt(secret_key.encode())
    
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
                           g_discount=10)

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
