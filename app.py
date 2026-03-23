import os
import base64
import requests
import concurrent.futures
from functools import wraps
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, Response, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import re
from fpdf import FPDF
import io

app = Flask(__name__)

def get_ist():
    # Render servers are UTC. IST is UTC+5:30.
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

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
    timestamp = db.Column(db.DateTime, default=get_ist)
    symbol = db.Column(db.String(100), default="ALGO")
    trade_type = db.Column(db.String(50), default="SIGNAL")
    entry_price = db.Column(db.Float, default=0.0)
    exit_price = db.Column(db.Float, default=0.0)
    sl_target = db.Column(db.String(20), default="None") # Target Hit, SL Hit
    points = db.Column(db.Float, default=0.0)
    signal_message = db.Column(db.String(500))
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Processed")

# ---------------------------------------------------------
# REGISTRATION & ROUTES
# ---------------------------------------------------------

# Create tables
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Database creation error: {e}")

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard', user_id=session['user_id']))
    return redirect(url_for('demo_register'))

@app.route('/demo-register', methods=['GET', 'POST'])
def demo_register():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard', user_id=session['user_id']))
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
            is_approved=True,
            expiry_date=get_ist() + timedelta(days=7),
            algo_status='ON'
        )
        db.session.add(new_user)
        try:
            db.session.commit()
            session.permanent = True
            session['user_id'] = new_user.id
            return redirect(url_for('user_dashboard', user_id=new_user.id))
        except:
            db.session.rollback()
            # If user already exists, just log them in and redirect to dashboard
            existing_user = User.query.filter((User.email == email) | (User.phone == phone)).first()
            if existing_user:
                session.permanent = True
                session['user_id'] = existing_user.id
                return redirect(url_for('user_dashboard', user_id=existing_user.id))
            return "Registration failed. Email or Phone might already be in use."
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard', user_id=session['user_id']))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        user = User.query.filter((User.email == identifier) | (User.phone == identifier)).first()
        if user:
            session.permanent = True
            session['user_id'] = user.id
            flash(f"Welcome back, {user.username}!")
            return redirect(url_for('user_dashboard', user_id=user.id))
        else:
            flash("User not found. Please register first.")
            return redirect(url_for('demo_register'))
            
    return render_template('login.html')

@app.route('/plans')
def subscription_plans():
    return render_template('plans.html')

# 🌟 USER DASHBOARD ROUTE (With Specific PnL Logic)
@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    # Ensure session or direct ID access
    session['user_id'] = user_id
    user = User.query.get_or_404(user_id)
    now = get_ist()
    today_date = now.date()
    remaining_days = (user.expiry_date - now).days if user.expiry_date else 0
    
    # 🌟 UPDATED: Keep history for 30 days to calculate P&L summaries
    # Delete only records older than 30 days
    limit_date = now - timedelta(days=30)
    TradeHistory.query.filter(TradeHistory.timestamp < limit_date).delete()
    db.session.commit()

    # --- Calculate Dynamic P&L ---
    total_trades = TradeHistory.query.all()
    
    pnl_1d = 0
    pnl_10d = 0
    pnl_20d = 0
    pnl_30d = 0
    
    # 🌟 NEW: Daily P&L Breakdown for the last 30 days
    daily_pnl = []
    for i in range(30):
        target_date = (now - timedelta(days=i)).date()
        day_pnl = sum(t.pnl for t in total_trades if t.timestamp.date() == target_date)
        daily_pnl.append({
            "day": i + 1,
            "date": target_date.strftime('%d-%b'),
            "pnl": round(day_pnl, 2)
        })

    for t in total_trades:
        days_diff = (now - t.timestamp).days
        if t.timestamp.date() == now.date(): pnl_1d += t.pnl
        if days_diff <= 10: pnl_10d += t.pnl
        if days_diff <= 20: pnl_20d += t.pnl
        if days_diff <= 30: pnl_30d += t.pnl
    
    return render_template('user.html', 
                           user=user, 
                           remaining_days=max(0, remaining_days),
                           discount_percent=user.personal_discount + 10,
                           pnl_1d=round(pnl_1d, 2),
                           pnl_10d=round(pnl_10d, 2),
                           pnl_20d=round(pnl_20d, 2),
                           pnl_30d=round(pnl_30d, 2),
                           daily_pnl=daily_pnl)


# ---------------------------------------------------------
# TRADING LOGIC (The Mechanism)
# ---------------------------------------------------------

@app.route('/tv-webhook', methods=['POST'])
def handle_tradingview_alert():
    alert_data = request.json # TradingView Message
    signal_msg = alert_data.get("message", "TV Signal Received")
    
    # Enhanced Parsing Logic
    pnl_value = 0.0
    entry = 0.0
    exit_p = 0.0
    pts = 0.0
    sl_t = "None"
    
    # 1. Parse Prices & Points
    price_match = re.search(r'(?:Price|Entry|at):\s*([-+]?\d*\.?\d+)', signal_msg, re.IGNORECASE)
    entry = float(price_match.group(1)) if price_match else 0.0
    
    points_match = re.search(r'(?:Profit|Loss|Pts|Points):\s*([-+]?\d*\.?\d+)', signal_msg, re.IGNORECASE)
    if points_match:
        pts = float(points_match.group(1))
        # If it's a Nifty signal, multiply by 65 as per user request
        if "NIFTY" in signal_msg.upper():
            pnl_value = pts * 65
        else:
            pnl_value = pts
    
    # Detect SL or Target
    if "TARGET" in signal_msg.upper() or "HIT" in signal_msg.upper():
        sl_t = "Target Hit"
        exit_p = entry + pts if pts > 0 else entry
    elif "SL" in signal_msg.upper() or "STOPLOSS" in signal_msg.upper() or "EXIT" in signal_msg.upper():
        sl_t = "SL Hit"
        exit_p = entry - abs(pts) if pts != 0 else entry

    # 2. Extract Cleaner Symbol Name
    symbol_match = re.search(r'([A-Z\s]+[0-9]*)', signal_msg)
    clean_symbol = symbol_match.group(1).strip() if symbol_match else "ALGO TRADE"

    # Detect Trade Type
    t_type = "SIGNAL"
    msg_upper = signal_msg.upper()
    if "BUY" in msg_upper: t_type = "BUY"
    elif "SELL" in msg_upper: t_type = "SELL"
    elif "TARGET" in msg_upper or "HIT" in msg_upper: t_type = "TARGET"
    elif "EXIT" in msg_upper or "SL" in msg_upper or "STOPLOSS" in msg_upper: t_type = "STOPLOSS"

    new_trade = TradeHistory(
        symbol=clean_symbol,
        trade_type=t_type,
        entry_price=entry,
        exit_price=exit_p,
        sl_target=sl_t,
        points=pts,
        signal_message=signal_msg, 
        pnl=pnl_value, 
        timestamp=get_ist()
    )
    db.session.add(new_trade)
    db.session.commit()
    
    # 2. Filter REAL Users
    real_active_users = User.query.filter_by(user_type='REAL', is_approved=True, algo_status='ON', admin_kill_switch=False).all()
    
    def execute_trade(u):
        with app.app_context():
            if u.expiry_date and u.expiry_date > get_ist():
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

@app.route('/approve-user', methods=['POST'])
@requires_auth
def approve_user():
    user_id = int(request.form.get('user_id'))
    plan = request.form.get('plan')
    months = int(request.form.get('months', 1))
    
    user = User.query.get_or_404(user_id)
    user.user_type = 'REAL'
    user.selected_plan = plan or "Basic"
    user.is_approved = True
    
    now_ist = get_ist()
    if user.expiry_date and user.expiry_date > now_ist:
        user.expiry_date = user.expiry_date + timedelta(days=30 * months)
    else:
        user.expiry_date = now_ist + timedelta(days=30 * months)
        
    db.session.commit()
    flash(f"User {user.username} Approved Successfully!")
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
    # Show only TODAY's trades in the History table
    today_date = get_ist().date()
    history = TradeHistory.query.filter(db.func.date(TradeHistory.timestamp) == today_date).order_by(TradeHistory.timestamp.desc()).all()
    total_pnl = round(sum((t.pnl for t in history if t.pnl)), 2)
    return render_template('history.html', trades=history, total_pnl=total_pnl)

@app.route('/download-pnl')
def download_pnl():
    # PDF report shows only TODAY's trades
    today_date = get_ist().date()
    trades = TradeHistory.query.filter(db.func.date(TradeHistory.timestamp) == today_date).all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Daily Trade Summary Report", ln=True, align='C')
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Arial", 'B', size=10)
    pdf.cell(40, 10, "Time", 1)
    pdf.cell(50, 10, "Symbol", 1)
    pdf.cell(30, 10, "Type", 1)
    pdf.cell(40, 10, "PnL (INR)", 1)
    pdf.cell(30, 10, "Status", 1)
    pdf.ln()

    # Table Body
    pdf.set_font("Arial", size=9)
    total = 0
    for t in trades:
        pdf.cell(40, 10, t.timestamp.strftime('%H:%M:%S'), 1)
        pdf.cell(50, 10, t.symbol[:25], 1)
        pdf.cell(30, 10, t.trade_type, 1)
        pdf.cell(40, 10, str(round(t.pnl, 2)), 1)
        pdf.cell(30, 10, t.status, 1)
        pdf.ln()
        total += t.pnl

    pdf.ln(5)
    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(200, 10, txt=f"Total Daily P&L: INR {round(total, 2)}", ln=True)

    stream = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    stream.write(pdf_output)
    stream.seek(0)
    
    return Response(stream, mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=daily_pnl_report.pdf"})

# 🌟 NEW: Dashboard Controls
@app.route('/toggle-algo/<int:user_id>', methods=['POST'])
def toggle_algo(user_id):
    user = User.query.get_or_404(user_id)
    user.algo_status = 'OFF' if user.algo_status == 'ON' else 'ON'
    db.session.commit()
    flash(f"Algo is now {user.algo_status}")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/save_api_settings', methods=['POST'])
def save_api_settings():
    user_id = int(request.form.get('user_id'))
    webhook_url = request.form.get('webhook_url')
    secret_key = request.form.get('secret_key')
    
    user = User.query.get_or_404(user_id)
    user.dhan_webhook_url = webhook_url
    if secret_key and secret_key != '********':
        user.encrypted_secret_key = cipher.encrypt(secret_key.encode())
    
    db.session.commit()
    flash("API Settings Saved Successfully!")
    return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/clear-history')
@requires_auth
def clear_history():
    db.session.query(TradeHistory).delete()
    db.session.commit()
    return redirect(url_for('trade_history'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully!")
    return redirect(url_for('demo_register'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
