import os
import hashlib
import time
import threading
from datetime import datetime, timedelta
from flask import request, jsonify, abort
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurityEngine")

# 🛡️ GVN MASTER ALGO - AI SECURITY ENGINE (V2.0)
# Comprehensive security: Firewall, DDoS protection, File integrity, Audit logging

class SecurityShield:
    def __init__(self, app=None, db=None, tg_sender=None):
        self.app = app
        self.db = db
        self.tg_sender = tg_sender
        self.blocked_ips = set()
        self.whitelist_ips = set()
        self.request_history = {} # IP: [timestamps]
        self.file_hashes = {}
        self.audit_log = []
        
        # Critical files to monitor
        self.critical_files = [
            'app.py', 
            'broker_api.py', 
            'nse_option_chain.py', 
            'gvn_master_robot.py',
            'gvn_levels_engine.py',
            'gvn_delta_levels_engine.py',
            'security_engine.py',
            'shared_data.py',
            '.env'
        ]
        
        self.attack_mode = False  # "AI Fever" mode - heightened security
        self.monitoring_active = False
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        logger.info("🛡️ [SECURITY] Initializing Security Shield...")
        
        # Compute initial file hashes (Skip on Render to avoid environment mismatches)
        if not os.environ.get('RENDER'):
            self._compute_initial_hashes()
        else:
            logger.info("ℹ️ [SECURITY] Integrity monitoring skipped on Render environment")
        
        # Start background monitoring threads
        self.monitoring_active = True
        threading.Thread(target=self._integrity_worker, daemon=True).start()
        threading.Thread(target=self._audit_log_worker, daemon=True).start()
        
        logger.info("✅ [SECURITY] Security Shield Active")
        
        # Register Flask middleware
        @app.before_request
        def shield_middleware():
            # Extract actual client IP behind proxies/Cloudflare
            x_forwarded = request.headers.get('X-Forwarded-For')
            if x_forwarded:
                ip = x_forwarded.split(',')[0].strip()
            else:
                ip = request.remote_addr
            
            # Bypass security blocking entirely for authenticated user/admin sessions
            from flask import session
            if session.get('user_id') or session.get('admin_logged_in'):
                return None
            
            # 1. Whitelist check (Local & Private Network)
            if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
                return None  # Allow immediately
            
            if ip in self.whitelist_ips:
                return None
            
            # 2. Block known malicious IPs
            if ip in self.blocked_ips:
                self._log_security_event("BLOCKED_IP_ACCESS", ip, request.path, "IP permanently blocked")
                return abort(403, description="🛑 GVN SECURITY: Your IP is blocked due to suspicious activity.")

            # 3. Bot Detection (User-Agent Filtering)
            ua = request.headers.get('User-Agent', '').lower()
            malicious_bots = ['python-requests', 'curl', 'wget', 'postman', 'headless', 'scraper', 'zgrab', 'masscan']
            if any(bot in ua for bot in malicious_bots):
                # Check if it's a legitimate internal request first
                if ip not in ['127.0.0.1', 'localhost']:
                    self._log_security_event("BOT_DETECTED", ip, request.path, f"Blocked malicious UA: {ua}")
                    return abort(403, description="🤖 Security Alert: Bot activity detected and blocked.")

            # 4. Rate Limiting / Bot Detection
            if self._is_suspicious(ip):
                self.block_ip(ip, "High Frequency Request (DDoS/Bot)")
                self._log_security_event("DDoS_ATTEMPT", ip, request.path, "Rate limit exceeded")
                return abort(429, description="🚨 Security Alert: Too many requests. Try again later.")

            # 5. Path Traversal / Common Attack Patterns
            path = request.path.lower()
            suspicious_patterns = ['.php', '.env', 'wp-admin', 'config', 'setup', 'eval(', 'base64_decode', '../', 'shell', '.git', 'etc/passwd']
            if any(p in path for p in suspicious_patterns):
                self.block_ip(ip, f"Accessing restricted path: {path}")
                self._log_security_event("MALICIOUS_PATH", ip, path, "Suspicious pattern detected")
                return abort(403, description="🛑 Access Denied")

            # 6. SQL Injection / Script Injection patterns
            suspicious_sql_patterns = ["' OR '1'='1", "UNION SELECT", "DROP TABLE", "INSERT INTO", "DELETE FROM", "<SCRIPT>", "JAVASCRIPT:"]
            full_data = str(request.args) + str(request.form) + str(request.get_json(silent=True) or {})
            if any(pattern in full_data.upper() for pattern in suspicious_sql_patterns):
                self.block_ip(ip, "Injection Attempt")
                self._log_security_event("INJECTION_ATTEMPT", ip, request.path, "Pattern detected")
                return abort(403)

    def _compute_initial_hashes(self):
        """Compute SHA256 hashes of all critical files for integrity monitoring"""
        logger.info("📁 [SECURITY] Computing file integrity hashes...")
        
        for file in self.critical_files:
            try:
                if os.path.exists(file):
                    with open(file, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        self.file_hashes[file] = file_hash
                        logger.debug(f"✓ Hashed {file}: {file_hash[:8]}...")
            except Exception as e:
                logger.error(f"Error hashing {file}: {e}")
        
        logger.info(f"✅ [SECURITY] Locked {len(self.file_hashes)} critical files")

    def _integrity_worker(self):
        """Background worker: Check file integrity every 60 seconds"""
        logger.info("🔍 [INTEGRITY MONITOR] Starting file integrity checks...")
        
        while self.monitoring_active:
            try:
                time.sleep(60)  # Check every minute
                
                for file, original_hash in self.file_hashes.items():
                    try:
                        if os.path.exists(file):
                            with open(file, 'rb') as f:
                                current_hash = hashlib.sha256(f.read()).hexdigest()
                                
                                if current_hash != original_hash:
                                    msg = (
                                        f"⚠️ <b>CRITICAL: FILE INTEGRITY BREACH!</b> ⚠️\n"
                                        f"📁 <b>File:</b> <code>{file}</code>\n"
                                        f"🕒 <b>Detected:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                        f"🔐 <b>Expected Hash:</b> {original_hash[:16]}...\n"
                                        f"⚡ <b>Current Hash:</b> {current_hash[:16]}...\n\n"
                                        f"⚠️ <i>Immediate Admin Review Required!</i>"
                                    )
                                    logger.critical(f"FILE MODIFIED: {file}")
                                    self._log_security_event("FILE_MODIFIED", "SYSTEM", file, f"Hash mismatch detected")
                                    
                                    if self.tg_sender:
                                        self.tg_sender(msg)
                    except Exception as e:
                        logger.error(f"Error checking {file}: {e}")
            
            except Exception as e:
                logger.error(f"Integrity worker error: {e}")

    def _audit_log_worker(self):
        """Background worker: Periodically save audit log"""
        while self.monitoring_active:
            try:
                time.sleep(300)  # Save every 5 minutes
                self._save_audit_log()
            except Exception as e:
                logger.error(f"Audit log worker error: {e}")

    def _log_security_event(self, event_type, ip, path, description):
        """Log security events for audit trail"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "ip": ip,
            "path": path,
            "description": description
        }
        self.audit_log.append(event)
        
        # Keep last 1000 events
        if len(self.audit_log) > 1000:
            self.audit_log.pop(0)
        
        logger.warning(f"[AUDIT] {event_type}: {ip} → {path} | {description}")

    def _is_suspicious(self, ip):
        """Rate limiting: Detect DDoS/Bot activity"""
        now = datetime.now()
        
        if ip not in self.request_history:
            self.request_history[ip] = []
        
        # Keep only last 1 minute of requests
        self.request_history[ip] = [t for t in self.request_history[ip] 
                                    if now - t < timedelta(seconds=60)]
        self.request_history[ip].append(now)
        
        # Set rate limit based on endpoint
        limit = 60  # Default: 60 req/min
        
        restricted_paths = ['/login', '/tv-webhook', '/demo-register', '/api/execute']
        if any(path in request.path for path in restricted_paths):
            limit = 30  # Sensitive endpoints: 30 req/min
        
        # In attack mode, reduce limits by 50%
        if self.attack_mode:
            limit = limit // 2
            logger.warning(f"🚨 ATTACK MODE: Rate limit reduced to {limit} req/min")
        
        requests_this_minute = len(self.request_history[ip])
        
        if requests_this_minute > limit:
            logger.warning(f"⚠️ Rate limit exceeded for {ip}: {requests_this_minute}/{limit}")
            return True
        
        return False

    def block_ip(self, ip, reason):
        """Add IP to permanent blocklist"""
        if ip not in self.blocked_ips and ip not in self.whitelist_ips:
            self.blocked_ips.add(ip)
            
            msg = (
                f"🚫 <b>GVN FIREWALL: IP BLOCKED</b> 🚫\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 <b>IP:</b> <code>{ip}</code>\n"
                f"🚨 <b>Reason:</b> {reason}\n"
                f"🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <i>Security System Monitoring...</i>"
            )
            
            logger.error(f"🚫 [SECURITY] Blocked IP: {ip} | Reason: {reason}")
            self._log_security_event("IP_BLOCKED", ip, "FIREWALL", reason)
            
            if self.tg_sender:
                self.tg_sender(msg)

    def whitelist_ip(self, ip):
        """Add IP to whitelist (trusted)"""
        self.whitelist_ips.add(ip)
        logger.info(f"✅ [SECURITY] Whitelisted IP: {ip}")
        self._log_security_event("IP_WHITELISTED", ip, "FIREWALL", "IP added to whitelist")

    def enable_attack_mode(self):
        """Enable heightened security (50% rate limit reduction)"""
        self.attack_mode = True
        logger.warning("🚨 [SECURITY] ATTACK MODE ENABLED - Heightened monitoring active!")
        msg = "🚨 <b>GVN SECURITY: ATTACK MODE ACTIVATED!</b>\nHeightened DDoS/Bot protection enabled.\nAll rate limits reduced by 50%."
        if self.tg_sender:
            self.tg_sender(msg)

    def disable_attack_mode(self):
        """Disable attack mode"""
        self.attack_mode = False
        logger.info("✅ [SECURITY] Attack mode disabled - Normal security levels restored")

    def _save_audit_log(self):
        """Save audit log to file for analysis"""
        try:
            log_file = "security_audit_log.json"
            with open(log_file, 'w') as f:
                json.dump(self.audit_log, f, indent=2)
            logger.debug(f"📁 Audit log saved: {len(self.audit_log)} events")
        except Exception as e:
            logger.error(f"Error saving audit log: {e}")

    def get_security_stats(self):
        """Get current security statistics"""
        return {
            "total_blocked_ips": len(self.blocked_ips),
            "total_whitelisted_ips": len(self.whitelist_ips),
            "attack_mode_active": self.attack_mode,
            "critical_files_monitored": len(self.file_hashes),
            "audit_log_entries": len(self.audit_log),
            "recent_events": self.audit_log[-10:]  # Last 10 events
        }

    def reset_integrity_hashes(self):
        """Re-compute hashes for all critical files (Authorized Reset)"""
        logger.info("🛡️ [SECURITY] Resetting file integrity hashes (Authorized Update)...")
        self._compute_initial_hashes()
        self._log_security_event("INTEGRITY_RESET", "ADMIN", "SYSTEM", "Authorized hash update performed")
        return True

    def log_authorized_modification(self, filename, reason):
        """Logs an authorized file modification to prevent panic alerts"""
        logger.info(f"✅ [SECURITY] Authorized modification logged for {filename}: {reason}")
        self._log_security_event("AUTHORIZED_MOD", "ADMIN", filename, reason)
        # Update the hash for this specific file immediately
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    new_hash = hashlib.sha256(f.read()).hexdigest()
                    self.file_hashes[filename] = new_hash
                    logger.info(f"✓ Updated hash for {filename}")
        except Exception as e:
            logger.error(f"Error updating hash for {filename}: {e}")

    def get_audit_log(self, limit=100):
        """Retrieve audit log entries"""
        return self.audit_log[-limit:]

    def stop(self):
        """Stop monitoring and cleanup"""
        logger.info("🛑 [SECURITY] Stopping Security Shield...")
        self.monitoring_active = False
