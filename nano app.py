import os
import requests
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from cryptography.fernet import Fernet # Security కోసం

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gvn_secure_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gvn_algo_pro.db'
db = SQLAlchemy(app)

# Encryption Key (దీన్ని సురక్షితంగా ఉంచుకోవాలి)
# ఒకవేళ సర్వర్ హ్యాక్ అయినా Secret Keys బయటపడవు.
cipher_key = Fernet.generate_key()
cipher = Fernet(cipher_key)

# ---------------------------------------------------------
# DATABASE MODELS
# ---------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    
    # Subscription Details
    selected_plan = db.Column(db.String(20)) # Basic, Premium, Ultimate
    is_approved = db.Column(db.Boolean, default=False) # Admin Approval
    expiry_date = db.Column(db.DateTime)
    
    # API & Algo Control
    dhan_webhook_url = db.Column(db.String(200))
    encrypted_secret_key = db.Column(db.LargeBinary)
    algo_status = db.Column(db.String(10), default='OFF') # User side ON/OFF
    admin_kill_switch = db.Column(db.Boolean, default=False) # Admin side OFF
    
    # Discounts
    personal_discount = db.Column(db.Integer, default=0) # Bargaining discount

# ---------------------------------------------------------
# TRADING LOGIC (The Mechanism)
# ---------------------------------------------------------

@app.route('/tv-webhook', methods=['POST'])
def handle_tradingview_alert():
    """
    ట్రేడింగ్‌వ్యూ నుండి అలర్ట్ వచ్చినప్పుడు ఈ ఫంక్షన్ రన్ అవుతుంది.
    ఇది డేటాబేస్‌లోని ప్రతి యాక్టివ్ యూజర్‌ని చెక్ చేసి ఆర్డర్ పంపుతుంది.
    """
    alert_data = request.json # TradingView Message
    
    # Filter only Active, Approved, and Not Expired users
    active_users = User.query.filter_by(is_approved=True, algo_status='ON', admin_kill_switch=False).all()
    
    for user in active_users:
        # Check Expiry
        if user.expiry_date and user.expiry_date > datetime.now():
            try:
                # Decrypt the secret key for this trade execution
                secret_key = cipher.decrypt(user.encrypted_secret_key).decode()
                
                # Prepare Order Payload for Dhan
                # ఇక్కడ మనం యూజర్ సేవ్ చేసిన URL కి డేటాను పంపుతాము
                dhan_payload = {
                    "secret": secret_key,
                    "alert_msg": alert_data.get("message", "TV Signal Received")
                }
                
                requests.post(user.dhan_url, json=dhan_payload, timeout=5)
                print(f"Trade Success for: {user.username}")
                
            except Exception as e:
                print(f"Trade Failed for {user.username}: {e}")
        else:
            # Auto-deactivate if expired
            user.algo_status = 'OFF'
            db.session.commit()
            
    return "Signals Processed", 200

# ---------------------------------------------------------
# DASHBOARD LOGIC (Admin & User)
# ---------------------------------------------------------

@app.route('/admin-control')
def admin_dashboard():
    all_users = User.query.all()
    global_discount = 10 # మీరు కావాలంటే దీన్ని కూడా డైనమిక్ చేయవచ్చు
    return render_template('admin.html', users=all_users, g_discount=global_discount)

@app.route('/approve-user/<int:user_id>/<int:months>')
def approve_user(user_id, months):
    user = User.query.get(user_id)
    user.is_approved = True
    user.expiry_date = datetime.now() + timedelta(days=30 * months)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/toggle-kill-switch/<int:user_id>')
def toggle_kill_switch(user_id):
    user = User.query.get(user_id)
    user.admin_kill_switch = not user.admin_kill_switch
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # First time డేటాబేస్ క్రియేట్ చేస్తుంది
    app.run(debug=True, port=5000)