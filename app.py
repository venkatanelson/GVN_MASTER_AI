<!DOCTYPE html>
<html lang="te">
<head>
    <meta charset="UTF-8">
    <title>GVN Algo - Admin</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }
        .admin-container { max-width: 1200px; margin: auto; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h2 { color: #1a73e8; border-bottom: 2px solid #e8f0fe; padding-bottom: 10px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: white; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; font-size: 14px; }
        th { background-color: #f8f9fa; color: #333; }
        
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; color: white; display: inline-block;}
        .btn-call { background: #ff9800; }
        .btn-approve { background: #28a745; }
        .btn-stop { background: #dc3545; }
        
        /* 🌟 NEW: Option Chain Pulse Style */
        .live-pulse { animation: pulse 2s infinite; }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .strike-pill { background: #e8f0fe; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; color: #1a73e8; }
        .delta-pill { background: #fef7e0; padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; color: #ea8600; }
    </style>
</head>
<body>

<div class="admin-container">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ddd; margin-bottom: 20px; padding-bottom: 10px;">
        <h1 style="margin: 0;">🚀 GVN Algo Master Admin Control</h1>
        <div>
            <a href="/admin/global-kill-switch" class="btn btn-stop" style="font-size: 14px; font-weight: bold; margin-right: 10px; background-color:#ff0000; box-shadow: 0 4px 8px rgba(255,0,0,0.3);" onclick="return confirm('⚠️ WARNING: This will FORCE EXIT ALL TRADES for ALL USERS across all brokers. Proceed?');">🚨 GLOBAL KILL SWITCH 🚨</a>
            <a href="/ai-dashboard" class="btn btn-approve" style="font-size: 14px; font-weight: bold; margin-right: 10px; background-color:#6366f1; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">🤖 AI Paper Trade Engine</a>
            <a href="/" class="btn btn-stop" style="font-size: 14px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">🚪 Logout / Home</a>
        </div>
    </div>

    <!-- 🛡️ AI SECURITY SYSTEM DASHBOARD -->
    <div class="card" style="border-top: 5px solid #dc3545; background: #fff5f5;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2 style="color: #dc3545; margin: 0;">🛡️ AI Security System (Antivirus & Firewall)</h2>
            <div id="security-badge" style="padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; background: #28a745; color: white;">
                SYSTEM SECURE
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 20px;">
            <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ffccd5; text-align: center;">
                <small style="color: #666; font-weight: bold;">ATTACK MODE</small><br>
                <span id="attack-mode-status" style="font-size: 18px; font-weight: bold; color: {{ '#ff0000' if config.attack_mode else '#28a745' }};">
                    {{ '🔥 FEVER (ULTRA)' if config.attack_mode else '🟢 NORMAL' }}
                </span>
            </div>
            <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ffccd5; text-align: center;">
                <small style="color: #666; font-weight: bold;">BLOCKED IPs</small><br>
                <span id="blocked-count" style="font-size: 18px; font-weight: bold; color: #dc3545;">0</span>
            </div>
            <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ffccd5; text-align: center;">
                <small style="color: #666; font-weight: bold;">INTEGRITY MONITOR</small><br>
                <span style="font-size: 18px; font-weight: bold; color: #1a73e8;">🔒 LOCKED</span>
            </div>
            <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #ffccd5; text-align: center;">
                <small style="color: #666; font-weight: bold;">SENSITIVITY</small><br>
                <span id="sensitivity-level" style="font-size: 18px; font-weight: bold; color: #ff9800;">AI ACTIVE</span>
            </div>
        </div>
        
        <div style="margin-top: 20px; display: flex; gap: 15px; justify-content: center;">
            <a href="/admin/toggle-attack-mode" class="btn {{ 'btn-approve' if config.attack_mode else 'btn-stop' }}" style="padding: 10px 20px; font-weight: bold;">
                {{ '🛑 DEACTIVATE FEVER MODE' if config.attack_mode else '🔥 ACTIVATE ATTACK MODE (FEVER)' }}
            </a>
            <a href="/admin/clear-firewall" class="btn" style="background: #6c757d; padding: 10px 20px; font-weight: bold;" onclick="return confirm('Clear all blocked IPs?');">🧹 CLEAR FIREWALL</a>
        </div>
        <p style="text-align: center; font-size: 12px; color: #dc3545; margin-top: 10px; font-weight: bold;">
            ⚠️ "Attack Mode" makes the AI extremely sensitive to request frequencies. Use only during active DDoS or Bot attacks.
        </p>
    </div>

    <!-- 🌟 NEW: DHAN OPTION CHAIN LIVE FEED -->
    <div class="card" style="border-top: 5px solid #6366f1; background: #f8f9ff;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h2 style="color: #6366f1; margin: 0;">📊 Dhan Option Chain Live Feed (Alpha Engine)</h2>
            <div style="font-size: 12px; color: #666; font-weight: bold;">
                <span class="live-pulse" style="color: #28a745;">●</span> LIVE UPDATING: <span id="oc-last-updated">--:--:--</span>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
            <!-- NIFTY -->
            <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #1a73e8;">
                <h4 style="margin: 0 0 10px 0; color: #1a73e8;">NIFTY 50</h4>
                <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;" id="nifty-spot">₹0.00</div>
                <div style="font-size: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between;"><span>ATM Strike:</span> <span class="strike-pill" id="nifty-atm">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 CE:</span> <span class="delta-pill" id="nifty-ce">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 PE:</span> <span class="delta-pill" id="nifty-pe">0</span></div>
                </div>
            </div>
            
            <!-- BANKNIFTY -->
            <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #9c27b0;">
                <h4 style="margin: 0 0 10px 0; color: #9c27b0;">BANKNIFTY</h4>
                <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;" id="banknifty-spot">₹0.00</div>
                <div style="font-size: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between;"><span>ATM Strike:</span> <span class="strike-pill" id="banknifty-atm">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 CE:</span> <span class="delta-pill" id="banknifty-ce">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 PE:</span> <span class="delta-pill" id="banknifty-pe">0</span></div>
                </div>
            </div>
            
            <!-- FINNIFTY -->
            <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #009688;">
                <h4 style="margin: 0 0 10px 0; color: #009688;">FINNIFTY</h4>
                <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;" id="finnifty-spot">₹0.00</div>
                <div style="font-size: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between;"><span>ATM Strike:</span> <span class="strike-pill" id="finnifty-atm">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 CE:</span> <span class="delta-pill" id="finnifty-ce">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 PE:</span> <span class="delta-pill" id="finnifty-pe">0</span></div>
                </div>
            </div>
            
            <!-- SENSEX -->
            <div style="background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #ff5722;">
                <h4 style="margin: 0 0 10px 0; color: #ff5722;">SENSEX</h4>
                <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;" id="sensex-spot">₹0.00</div>
                <div style="font-size: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between;"><span>ATM Strike:</span> <span class="strike-pill" id="sensex-atm">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 CE:</span> <span class="delta-pill" id="sensex-ce">0</span></div>
                    <div style="display: flex; justify-content: space-between;"><span>Delta 60 PE:</span> <span class="delta-pill" id="sensex-pe">0</span></div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function updateSecurityStatus() {
        // 🛡️ Update Security
        fetch('/admin/security-status')
            .then(res => res.json())
            .then(data => {
                document.getElementById('blocked-count').innerText = data.blocked_count;
                const badge = document.getElementById('security-badge');
                if (data.attack_mode) {
                    badge.innerText = "🚨 UNDER ATTACK";
                    badge.style.background = "#ff0000";
                } else {
                    badge.innerText = "🟢 SYSTEM SECURE";
                    badge.style.background = "#28a745";
                }
            });
            
        // 📊 Update Option Chain Summary
        fetch('/api/gvn-scanner')
            .then(res => res.json())
            .then(data => {
                if (data.summary) {
                    const s = data.summary;
                    document.getElementById('oc-last-updated').innerText = s.last_updated || "--:--:--";
                    
                    // NIFTY
                    document.getElementById('nifty-spot').innerText = "₹" + (s.NIFTY.spot || 0).toLocaleString();
                    document.getElementById('nifty-atm').innerText = s.NIFTY.atm || 0;
                    document.getElementById('nifty-ce').innerText = s.NIFTY.ce_60 || 0;
                    document.getElementById('nifty-pe').innerText = s.NIFTY.pe_60 || 0;
                    
                    // BANKNIFTY
                    document.getElementById('banknifty-spot').innerText = "₹" + (s.BANKNIFTY.spot || 0).toLocaleString();
                    document.getElementById('banknifty-atm').innerText = s.BANKNIFTY.atm || 0;
                    document.getElementById('banknifty-ce').innerText = s.BANKNIFTY.ce_60 || 0;
                    document.getElementById('banknifty-pe').innerText = s.BANKNIFTY.pe_60 || 0;
                    
                    // FINNIFTY
                    document.getElementById('finnifty-spot').innerText = "₹" + (s.FINNIFTY.spot || 0).toLocaleString();
                    document.getElementById('finnifty-atm').innerText = s.FINNIFTY.atm || 0;
                    document.getElementById('finnifty-ce').innerText = s.FINNIFTY.ce_60 || 0;
                    document.getElementById('finnifty-pe').innerText = s.FINNIFTY.pe_60 || 0;
                    
                    // SENSEX
                    document.getElementById('sensex-spot').innerText = "₹" + (s.SENSEX.spot || 0).toLocaleString();
                    document.getElementById('sensex-atm').innerText = s.SENSEX.atm || 0;
                    document.getElementById('sensex-ce').innerText = s.SENSEX.ce_60 || 0;
                    document.getElementById('sensex-pe').innerText = s.SENSEX.pe_60 || 0;
                }
            });
    }
    setInterval(updateSecurityStatus, 5000);
    updateSecurityStatus();
    </script>

    <!-- DYNAMIC SYSTEM SETTINGS -->
    <div class="card" style="border-top: 5px solid #1a73e8; background: #e8f0fe;">
        <h2>⚙️ Dynamic System Settings</h2>
        <form action="/update-settings" method="POST" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div>
                <label><b>Admin Username:</b></label><br>
                <input type="text" name="admin_user" value="{{ config.admin_user }}" style="width: 90%; padding: 8px;" required>
            </div>
            <div>
                <label><b>Admin Password:</b></label><br>
                <div style="position: relative; width: 90%;">
                    <input type="password" id="admin_pass" name="admin_pass" value="{{ config.admin_pass }}" style="width: 100%; padding: 8px; box-sizing: border-box;" required>
                    <span onclick="togglePass()" style="position: absolute; right: 8px; top: 8px; cursor: pointer;" title="Show/Hide Password">👁️</span>
                </div>
            </div>
            <div>
                <label><b>Tech Support No (User Dashboard):</b></label><br>
                <input type="text" name="support_1" value="{{ config.support_number_1 }}" style="width: 90%; padding: 8px;">
            </div>
            <div>
                <label><b>Admin Contact No (User Dashboard):</b></label><br>
                <input type="text" name="support_2" value="{{ config.support_number_2 }}" style="width: 90%; padding: 8px;">
            </div>
            <div style="grid-column: span 2;">
                <label><b>Admin Recovery Phone (For Reset OTP):</b></label><br>
                <input type="text" name="admin_phone" value="{{ config.admin_phone }}" style="width: 45%; padding: 8px;" required>
            </div>
            <div style="grid-column: span 2; text-align: center; margin-top: 10px;">
                <button type="submit" class="btn btn-approve" style="padding: 10px 30px; font-size: 16px;">Save All Settings</button>
            </div>
        </form>
    </div>

    <!-- 💰 PENDING PAYMENTS -->
    <div class="card" style="border-top: 5px solid #28a745;">
        <h2>💰 Pending Payment Verifications (₹300 Signal Unlock)</h2>
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th>Plan</th>
                    <th>UTR / Transaction ID</th>
                    <th>Screenshot</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for p in pending_payments %}
                <tr>
                    <td><strong>ID: {{ p.user_id }}</strong></td>
                    <td><span style="background: #e8f0fe; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{{ p.plan_selected }}</span></td>
                    <td><code>{{ p.utr_number }}</code></td>
                    <td>
                        <a href="/static/uploads/payments/{{ p.screenshot_path }}" target="_blank">
                            <img src="/static/uploads/payments/{{ p.screenshot_path }}" style="height: 50px; border: 1px solid #ccc; border-radius: 5px;">
                            <br><small>View Full Size</small>
                        </a>
                    </td>
                    <td>
                        <form action="/approve-payment/{{ p.id }}" method="POST" style="display:flex; gap:5px;">
                            <button name="action" value="APPROVE" class="btn btn-approve" style="padding: 4px 8px; font-size:12px;">✅ Approve</button>
                            <button name="action" value="REJECT" class="btn btn-stop" style="padding: 4px 8px; font-size:12px;">❌ Reject</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align:center; color: #999;">No pending payment requests.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- REAL USERS -->
    <div class="card">
        <h2>🔥 Real Accounts (Total: {{ real_users|length }})</h2>
        <table>
            <thead>
                <tr>
                    <th>User Detail</th>
                    <th>Plan</th>
                    <th>Expiry Date</th>
                    <th>Algo Status</th>
                    <th>Signal Lock</th>
                    <th>Admin Approval</th>
                    <th>Master Control</th>
                </tr>
            </thead>
            <tbody>
                {% for user in real_users %}
                <tr style="{% if user.is_blocked %}background-color: #ffe6e6; opacity: 0.7;{% endif %}">
                    <td><strong>{{ user.username }}</strong><br><small>{{ user.phone }}</small></td>
                    <td>{{ user.selected_plan }}</td>
                    <td>{{ user.expiry_date.strftime('%d-%m-%Y') if user.expiry_date else 'N/A' }}</td>
                    <td>{{ user.algo_status }}</td>
                    <td>
                        <a href="/toggle-signal-lock/{{ user.id }}" class="btn" style="background: {{ '#dc3545' if user.is_locked else '#6c757d' }}; padding: 4px 8px; font-size: 11px;">
                            {{ '🔒 LOCKED' if user.is_locked else '🔓 UNLOCKED' }}
                        </a>
                    </td>
                    <td>
                        {% if not user.is_approved %}
                            <form action="/approve-user" method="POST" style="display:inline;">
                                <input type="hidden" name="user_id" value="{{ user.id }}">
                                <input type="hidden" name="plan" value="{{ user.selected_plan or 'Basic' }}">
                                <input type="hidden" name="months" value="1">
                                <button type="submit" class="btn btn-approve" style="padding: 4px 8px; font-size:11px;">Approve (1M)</button>
                            </form>
                        {% else %}
                            <span style="color: green; font-weight: bold; font-size:12px;">✅ Approved</span>
                        {% endif %}
                    </td>
                    <td>
                        <a href="/admin/force-square-off/{{ user.id }}" class="btn" style="padding: 6px 10px; font-size:11px; background-color:#000; color:#fff;" onclick="return confirm('Force Exit ALL BROKER POSITIONS for {{ user.username }}?');">🛑 FORCE EXIT</a>
                        <a href="/toggle-kill-switch/{{ user.id }}" class="btn {{ 'btn-stop' if not user.admin_kill_switch else 'btn-approve' }}" style="padding: 6px 10px; font-size:11px; margin-left:2px;">
                            {{ 'MASTER STOP' if not user.admin_kill_switch else 'ENABLE' }}
                        </a>
                        <a href="/block-user/{{ user.id }}" class="btn" style="background: #e67e22; padding: 6px 10px; font-size:11px; margin-left:5px;" onclick="return confirm('Toggle BLOCK for this user?');">
                            {{ 'UNBLOCK' if user.is_blocked else '🚫 BLOCK' }}
                        </a>
                        <a href="/delete-user/{{ user.id }}" class="btn btn-stop" style="padding: 6px 10px; font-size:11px; margin-left:5px;" onclick="return confirm('Are you sure you want to completely delete this REAL user?');">🗑️ Delete</a>
                    </td>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- DEMO USERS -->
    <div class="card" style="border-left: 5px solid #ff9800;">
        <h2 style="color: #ff9800;">🎯 Demo Accounts (Total: {{ demo_users|length }})</h2>
        <table>
            <thead>
                <tr>
                    <th>User Detail</th>
                    <th>Email ID</th>
                    <th>Virtual Capital</th>
                    <th>Expiry Date</th>
                    <th>Algo Status</th>
                    <th>Signal Lock</th>
                    <th>Contact Action</th>
                </tr>
            </thead>
            <tbody>
                {% for user in demo_users %}
                <tr style="{% if user.is_blocked %}background-color: #ffe6e6; opacity: 0.7;{% endif %}">
                    <td><strong>{{ user.username }}</strong><br><small>{{ user.phone }}</small></td>
                    <td>{{ user.email }}</td>
                    <td>₹ {{ user.demo_capital }}</td>
                    <td>{{ user.expiry_date.strftime('%d-%m-%Y') if user.expiry_date else 'N/A' }}</td>
                    <td>{{ user.algo_status }}</td>
                    <td>
                        <a href="/toggle-signal-lock/{{ user.id }}" class="btn" style="background: {{ '#dc3545' if user.is_locked else '#6c757d' }}; padding: 4px 8px; font-size: 11px;">
                            {{ '🔒 LOCKED' if user.is_locked else '🔓 UNLOCKED' }}
                        </a>
                    </td>
                    <td>
                        <form action="/approve-user" method="POST" style="display:inline-block; margin-bottom:5px;">
                            <input type="hidden" name="user_id" value="{{ user.id }}">
                            <select name="plan" required style="padding:3px; font-size:12px;">
                                <option value="Basic">Basic (₹2999)</option>
                                <option value="Premium">Premium (₹5999)</option>
                                <option value="Ultimate">Ultimate (₹9999)</option>
                            </select>
                            <select name="months" style="padding:3px; font-size:12px;">
                                <option value="1">1 Month</option>
                                <option value="3">3 Months</option>
                                <option value="6">6 Months</option>
                            </select>
                            <button type="submit" class="btn btn-approve" style="padding: 4px 8px; font-size:12px;">Approve as Real</button>
                        </form>
                        <br>
                        <a href="/admin-extend-demo/{{ user.id }}" class="btn" style="background:#1a73e8; padding: 4px 8px; font-size:12px; margin-bottom:5px;" onclick="return confirm('Extend Demo for 1 Month?');">⏳ Extend 1 Month</a>
                        <br>
                        <a href="/admin/force-square-off/{{ user.id }}" class="btn" style="padding: 4px 8px; font-size:12px; margin-bottom:5px; background-color:#000; color:#fff;" onclick="return confirm('Force Exit trades for Demo user: {{ user.username }}?');">🛑 FORCE EXIT</a>
                        <a href="/toggle-kill-switch/{{ user.id }}" class="btn {{ 'btn-stop' if not user.admin_kill_switch else 'btn-approve' }}" style="padding: 4px 8px; font-size:12px; margin-bottom:5px;">
                            {{ 'MASTER STOP' if not user.admin_kill_switch else 'ENABLE ALGO' }}
                        </a>
                        <br>
                        <a href="tel:{{ user.phone }}" class="btn btn-call" style="padding: 4px 8px; font-size:12px;">📞 Call</a>
                        <a href="/block-user/{{ user.id }}" class="btn" style="background: #e67e22; padding: 4px 8px; font-size:12px; margin-left: 5px;" onclick="return confirm('Toggle BLOCK for this Demo user?');">
                            {{ 'UNBLOCK' if user.is_blocked else '🚫 BLOCK' }}
                        </a>
                        <a href="/delete-user/{{ user.id }}" class="btn btn-stop" style="padding: 4px 8px; font-size:12px; margin-left: 5px;" onclick="return confirm('Delete this Demo user?');">🗑️ Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

</div>

<script>
function togglePass() {
    var x = document.getElementById("admin_pass");
    if (x.type === "password") {
        x.type = "text";
    } else {
        x.type = "password";
    }
}
</script>
</body>
</html>
