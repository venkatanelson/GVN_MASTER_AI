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
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gvn_secure_2026')
db_url = os.environ.get('DATABASE_URL', 'sqlite:///gvn_algo_pro.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Encryption
static_key_32 = b'gvn_secure_key_for_encryption_26'
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', base64.urlsafe_b64encode(static_key_32))
cipher = Fernet(ENCRYPTION_KEY)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50)); phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True); user_type = db.Column(db.String(10), default='REAL')
    demo_capital = db.Column(db.Integer, default=50000); selected_plan = db.Column(db.String(20))
    is_approved = db.Column(db.Boolean, default=False); expiry_date = db.Column(db.DateTime)
    dhan_webhook_url = db.Column(db.String(300)); encrypted_secret_key = db.Column(db.LargeBinary)
    algo_status = db.Column(db.String(10), default='OFF'); admin_kill_switch = db.Column(db.Boolean, default=False)
    personal_discount = db.Column(db.Integer, default=0)

class TradeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True); timestamp = db.Column(db.DateTime, default=get_ist)
    symbol = db.Column(db.String(100)); trade_type = db.Column(db.String(50))
    entry_price = db.Column(db.Float, default=0.0); exit_price = db.Column(db.Float, default=0.0)
    sl_target = db.Column(db.String(20)); points = db.Column(db.Float, default=0.0)
    signal_message = db.Column(db.String(500)); pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Processed")

with app.app_context():
    try: db.create_all()
    except Exception as e: print(f"DB Error: {e}")

# Admin Auth
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == os.environ.get('ADMIN_USERNAME', 'admin') and auth.password == os.environ.get('ADMIN_PASSWORD', 'admin123')):
            return Response('Login required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('user_dashboard', user_id=session['user_id']))
    return redirect(url_for('demo_register'))

@app.route('/demo-register', methods=['GET', 'POST'])
def demo_register():
    if request.method == 'POST':
        u = request.form.get('username'); p = request.form.get('phone'); e = request.form.get('email')
        c = int(request.form.get('demo_capital', 50000))
        new_u = User(username=u, phone=p, email=e, user_type='DEMO', demo_capital=c, is_approved=True, expiry_date=get_ist()+timedelta(days=7), algo_status='ON')
        try:
            db.session.add(new_u); db.session.commit(); session['user_id'] = new_u.id
            return redirect(url_for('user_dashboard', user_id=new_u.id))
        except:
            db.session.rollback(); ex = User.query.filter((User.email == e) | (User.phone == p)).first()
            if ex: session['user_id'] = ex.id; return redirect(url_for('user_dashboard', user_id=ex.id))
            return "Registration Error"
    try: return render_template('register.html')
    except Exception as err: return f"Template Missing: register.html. Error: {err}", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        idnt = request.form.get('identifier')
        user = User.query.filter((User.email == idnt) | (User.phone == idnt)).first()
        if user: session['user_id'] = user.id; return redirect(url_for('user_dashboard', user_id=user.id))
        flash("User not found")
    try: return render_template('login.html')
    except Exception as err: return f"Template Missing: login.html. Error: {err}", 500

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    session['user_id'] = user_id; u = User.query.get_or_404(user_id); now = get_ist()
    TradeHistory.query.filter(TradeHistory.timestamp < now - timedelta(days=30)).delete()
    db.session.commit(); all_t = TradeHistory.query.all()
    p1, p10, p20, p30 = 0, 0, 0, 0; d_pnl = []
    for i in range(30):
        dt = (now - timedelta(days=i)).date()
        dp = sum(t.pnl for t in all_t if t.timestamp.date() == dt and t.pnl)
        d_pnl.append({"day": i+1, "date": dt.strftime('%d-%b'), "pnl": round(dp, 2)})
    for t in all_t:
        diff = (now - t.timestamp).days
        if t.timestamp.date() == now.date(): p1 += (t.pnl or 0)
        if diff <= 10: p10 += (t.pnl or 0)
        if diff <= 20: p20 += (t.pnl or 0)
        if diff <= 30: p30 += (t.pnl or 0)
    try: return render_template('user.html', user=u, pnl_1d=round(p1,2), pnl_10d=round(p10,2), pnl_20d=round(p20,2), pnl_30d=round(p30,2), daily_pnl=d_pnl)
    except Exception as err: return f"Template Missing: user.html. Error: {err}", 500

@app.route('/admin-control')
@requires_auth
def admin_dashboard():
    try: return render_template('admin.html', real_users=User.query.filter_by(user_type='REAL').all(), demo_users=User.query.filter_by(user_type='DEMO').all())
    except Exception as err: return f"Template Missing: admin.html. Error: {err}", 500

@app.route('/history')
def trade_history():
    try:
        today = get_ist().date()
        h = TradeHistory.query.filter(db.func.date(TradeHistory.timestamp) == today).order_by(TradeHistory.timestamp.desc()).all()
        tp = round(sum(t.pnl for t in h if t.pnl), 2)
        return render_template('history.html', trades=h, total_pnl=tp)
    except Exception as err: return f"History Error: {err}. Make sure history.html exists.", 500

@app.route('/approve-user', methods=['POST'])
@requires_auth
def approve_user():
    u = User.query.get_or_404(int(request.form.get('user_id')))
    u.user_type = 'REAL'; u.is_approved = True; u.selected_plan = request.form.get('plan')
    days = 30 * int(request.form.get('months', 1))
    u.expiry_date = (u.expiry_date if u.expiry_date and u.expiry_date > get_ist() else get_ist()) + timedelta(days=days)
    db.session.commit(); return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout(): session.pop('user_id', None); return redirect(url_for('demo_register'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
