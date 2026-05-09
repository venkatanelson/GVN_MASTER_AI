from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from security_vault import vault

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user') # admin, user
    
    # GVN Specific Fields
    algo_status = db.Column(db.String(10), default='OFF')
    user_type = db.Column(db.String(20), default='PAPER') # PAPER, LIVE
    is_approved = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    full_auto_mode = db.Column(db.Boolean, default=False)
    trade_lots = db.Column(db.Integer, default=1)
    demo_capital = db.Column(db.Float, default=100000.0)
    expiry_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    credentials = db.relationship('BrokerCredential', backref='owner', lazy=True)
    trades = db.relationship('TradeHistory', backref='owner', lazy=True)

class BrokerCredential(db.Model):
    __tablename__ = 'broker_credentials'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broker_name = db.Column(db.String(50), default="Shoonya") # Shoonya, Dhan, AngelOne
    client_id = db.Column(db.String(100))
    encrypted_password = db.Column(db.Text)
    encrypted_api_key = db.Column(db.Text)
    encrypted_api_secret = db.Column(db.Text)
    encrypted_totp_key = db.Column(db.Text)
    vendor_code = db.Column(db.String(100))
    
    def set_credentials(self, password=None, api_key=None, api_secret=None, totp_key=None):
        if password: self.encrypted_password = vault.encrypt(password)
        if api_key: self.encrypted_api_key = vault.encrypt(api_key)
        if api_secret: self.encrypted_api_secret = vault.encrypt(api_secret)
        if totp_key: self.encrypted_totp_key = vault.encrypt(totp_key)

    def get_credentials(self):
        return {
            "password": vault.decrypt(self.encrypted_password),
            "api_key": vault.decrypt(self.encrypted_api_key),
            "api_secret": vault.decrypt(self.encrypted_api_secret),
            "totp_key": vault.decrypt(self.encrypted_totp_key)
        }

class TradeHistory(db.Model):
    __tablename__ = 'trade_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(100))
    action = db.Column(db.String(10)) # BUY, SELL
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float, default=0.0)
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='COMPLETED') # COMPLETED, OPEN, FAILED
    entry_price = db.Column(db.Float, default=0.0)
    exit_price = db.Column(db.Float, default=0.0)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_name = db.Column(db.String(50), default='Basic')
    expires_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
