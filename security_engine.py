import os
import hashlib
import time
import threading
from datetime import datetime, timedelta
from flask import request, jsonify, abort
import requests

# 🛡️ GVN MASTER ALGO - AI SECURITY ENGINE (V1.0)
# This module acts as an Antivirus, Firewall, and Integrity Monitor.

class SecurityShield:
    def __init__(self, app=None, db=None, tg_sender=None):
        self.app = app
        self.db = db
        self.tg_sender = tg_sender
        self.blocked_ips = set()
        self.request_history = {} # IP: [timestamps]
        self.file_hashes = {}
        self.critical_files = [
            'app.py', 
            'broker_api.py', 
            'nse_option_chain.py', 
            'security_engine.py',
            '.env'
        ]
        self.attack_mode = False # "AI Fever" mode
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        # Initial Hash Computation
        self._compute_initial_hashes()
        
        # Start Background Integrity Monitor
        threading.Thread(target=self._integrity_worker, daemon=True).start()
        
        # Register Flask Middleware
        @app.before_request
        def shield_middleware():
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # 1. Block known malicious IPs
            if ip in self.blocked_ips:
                return abort(403, description="🛑 GVN SECURITY: Your IP is permanently blocked due to suspicious activity.")

            # 2. Rate Limiting / Bot Detection (AI Sensitivity)
            if self._is_suspicious(ip):
                self.block_ip(ip, "High Frequency Request (DDoS/Bot)")
                return abort(429, description="🚨 Security Alert: Potential Bot Detected.")

            # 3. Path Traversal / Common Attack Patterns
            path = request.path.lower()
            suspicious_patterns = ['.php', '.env', 'wp-admin', 'config', 'setup', 'eval(', 'base64_decode']
            if any(p in path for p in suspicious_patterns):
                self.block_ip(ip, f"Accessing restricted path: {path}")
                return abort(403)

    def _compute_initial_hashes(self):
        print("🛡️ [SECURITY] Computing critical file signatures...")
        for file in self.critical_files:
            if os.path.exists(file):
                with open(file, 'rb') as f:
                    self.file_hashes[file] = hashlib.sha256(f.read()).hexdigest()
        print("✅ [SECURITY] Signatures Locked.")

    def _integrity_worker(self):
        """Checks for unauthorized file modifications every 60 seconds."""
        while True:
            time.sleep(60)
            for file, original_hash in self.file_hashes.items():
                if os.path.exists(file):
                    with open(file, 'rb') as f:
                        current_hash = hashlib.sha256(f.read()).hexdigest()
                        if current_hash != original_hash:
                            msg = f"⚠️ <b>SECURITY BREACH DETECTED!</b> ⚠️\nFile: <code>{file}</code> has been modified!\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            print(f"🚨 [SECURITY ALERT] {file} modified!")
                            if self.tg_sender:
                                self.tg_sender(msg)
                            # Potential auto-restore logic could go here
                            # For now, we just alert and update hash if it was intentional? 
                            # No, let's keep alerting until admin acknowledges.

    def _is_suspicious(self, ip):
        now = datetime.now()
        if ip not in self.request_history:
            self.request_history[ip] = []
        
        # Keep only last 1 minute of requests
        self.request_history[ip] = [t for t in self.request_history[ip] if now - t < timedelta(seconds=60)]
        self.request_history[ip].append(now)
        
        # Threshold: 60 requests per minute for normal routes
        # 5 requests per minute for login/webhook routes
        limit = 60
        if request.path in ['/login', '/tv-webhook', '/demo-register']:
            limit = 30 # Increased to prevent blocking multiple concurrent strategy alerts
            
        # If Attack Mode is ON (AI Fever), reduce limits by 50%
        if self.attack_mode:
            limit = limit // 2
            
        if len(self.request_history[ip]) > limit:
            return True
        return False

    def block_ip(self, ip, reason):
        if ip not in self.blocked_ips:
            self.blocked_ips.add(ip)
            msg = (
                f"🚫 <b>GVN FIREWALL: IP BLOCKED</b> 🚫\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>IP:</b> <code>{ip}</code>\n"
                f"🚨 <b>Reason:</b> {reason}\n"
                f"🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <i>AI Security System is Monitoring...</i>"
            )
            print(f"🚫 [SECURITY] Blocked IP: {ip} | Reason: {reason}")
            if self.tg_sender:
                self.tg_sender(msg)

    def set_attack_mode(self, status):
        """Enable 'AI Fever' - Ultra Sensitivity Mode."""
        self.attack_mode = status
        mode_str = "🔥 ON (ULTRA SENSITIVE)" if status else "🟢 NORMAL"
        msg = f"🛡️ <b>GVN SECURITY: Attack Mode is {mode_str}</b>"
        if self.tg_sender:
            self.tg_sender(msg)
        print(f"🛡️ [SECURITY] Attack Mode set to {status}")

    def get_status(self):
        return {
            "attack_mode": self.attack_mode,
            "blocked_count": len(self.blocked_ips),
            "critical_files_status": "LOCKED",
            "uptime": "AI ACTIVE"
        }
