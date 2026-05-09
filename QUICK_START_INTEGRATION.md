# 🚀 GVN System Integration Guide (Quick Start)

## Phase 1: Update `app.py` (Flask Integration)

### Add imports at the top:
```python
from gvn_master_orchestrator import get_orchestrator
from gvn_paper_trading_engine import PaperTradingManager
import shared_data
```

### Add routes for the system status dashboard:
```python
@app.route('/api/system-status')
def system_status_api():
    try:
        orch = get_orchestrator()
        if not orch:
            return jsonify({"error": "Orchestrator not initialized"}), 500
        
        status = orch.get_system_status_report()
        return jsonify(status)
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/paper-trading')
def paper_trading_api():
    try:
        pm = PaperTradingManager()
        executor = pm.get_executor()
        stats = executor.get_performance_metrics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/gvn-levels')
def gvn_levels_api():
    try:
        return jsonify(shared_data.gvn_levels)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/market-sentiment')
def market_sentiment_api():
    try:
        return jsonify(shared_data.sentiment_history[-1:])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Update `init_gvn()` to initialize orchestrator:
```python
def init_gvn():
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists (already fixed)
        existing_user = User.query.filter_by(phone="9966123078").first()
        if not existing_user:
            v = User(id=1, username="Venkat", phone="9966123078", email="nelsonp143@gmail.com", 
                    is_admin=True, algo_status="OFF", user_type="LIVE")
            db.session.add(v)
            db.session.commit()
        
        # Initialize orchestrator
        try:
            admin_user = User.query.get(1)
            if admin_user and admin_user.broker_config:
                broker_config = {
                    "broker_name": admin_user.broker_config.broker_name or "Dhan",
                    "client_id": admin_user.broker_config.client_id,
                    "access_token": admin_user.broker_config.api_key,
                    "api_secret": admin_user.broker_config.api_secret,
                    "webhook_url": admin_user.broker_config.dhan_webhook_url or os.environ.get("WEBHOOK_URL"),
                    "quantity": admin_user.trade_lots
                }
                
                telegram_config = {
                    "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                    "chat_id": os.environ.get("TELEGRAM_CHAT_ID", "")
                }
                
                orch = get_orchestrator(broker_config, telegram_config)
                orch.initialize_system()
                logger.info("✅ GVN Orchestrator initialized")
        except Exception as e:
            logger.warning(f"⚠️ Orchestrator init skipped: {e}")
        
        # Start live feed
        try:
            import shoonya_live_feed
            shoonya_live_feed.start_live_feed_worker()
        except Exception as e:
            logger.warning(f"⚠️ Feed Worker Start Failed: {e}")
```

---

## Phase 2: Update `user.html` Dashboard

### Add new sections to the dashboard:

```html
<!-- GVN System Status Panel -->
<div class="dashboard-card" id="system-status">
    <h3>🎯 GVN System Status</h3>
    <div id="system-info">
        <p>Status: <span id="sys-status">Initializing...</span></p>
        <p>Mode: <span id="sys-mode">Loading...</span></p>
        <p>Active Trades: <span id="active-trades">0</span></p>
    </div>
</div>

<!-- Paper Trading Stats -->
<div class="dashboard-card" id="paper-trading-card">
    <h3>📊 Paper Trading Performance</h3>
    <div id="paper-stats">
        <p>Balance: ₹<span id="paper-balance">500000</span></p>
        <p>Total Trades: <span id="paper-trades">0</span></p>
        <p>Win Rate: <span id="win-rate">0%</span></p>
        <p>P&L: ₹<span id="paper-pnl">0</span></p>
    </div>
</div>

<!-- GVN Levels Display -->
<div class="dashboard-card" id="gvn-levels-card">
    <h3>📍 GVN i-Levels (Today)</h3>
    <div id="levels-grid">
        <div class="level i7">i7: <span id="level-i7">--</span></div>
        <div class="level i5">i5: <span id="level-i5">--</span></div>
        <div class="level i3">i3: <span id="level-i3">--</span></div>
        <div class="level i1">i1: <span id="level-i1">--</span></div>
    </div>
</div>

<!-- Market Sentiment -->
<div class="dashboard-card" id="sentiment-card">
    <h3>🔮 Market Sentiment</h3>
    <p id="sentiment-verdict">Waiting for market data...</p>
    <p>Verdict Score: <span id="sentiment-score">0/5</span></p>
    <p>PCR: <span id="sentiment-pcr">--</span></p>
</div>
```

### Add JavaScript to update every second:

```javascript
// Auto-update system status
setInterval(function() {
    // System Status
    fetch('/api/system-status')
        .then(r => r.json())
        .then(data => {
            document.getElementById('sys-status').textContent = data.system.initialized ? '✅ Active' : '⏳ Initializing';
            document.getElementById('sys-mode').textContent = data.system.mode;
            document.getElementById('active-trades').textContent = data.system.active_trades;
        });
    
    // Paper Trading
    fetch('/api/paper-trading')
        .then(r => r.json())
        .then(data => {
            document.getElementById('paper-balance').textContent = data.current_balance.toLocaleString();
            document.getElementById('paper-trades').textContent = data.total_trades;
            document.getElementById('win-rate').textContent = data.win_rate + '%';
            document.getElementById('paper-pnl').textContent = data.total_pnl.toLocaleString();
        });
    
    // GVN Levels
    fetch('/api/gvn-levels')
        .then(r => r.json())
        .then(data => {
            document.getElementById('level-i7').textContent = data.i7 || '--';
            document.getElementById('level-i5').textContent = data.i5 || '--';
            document.getElementById('level-i3').textContent = data.i3 || '--';
            document.getElementById('level-i1').textContent = data.i1 || '--';
        });
    
    // Market Sentiment
    fetch('/api/market-sentiment')
        .then(r => r.json())
        .then(data => {
            if (data && data.length > 0) {
                const sentiment = data[0];
                document.getElementById('sentiment-verdict').textContent = sentiment.verdict;
                document.getElementById('sentiment-score').textContent = sentiment.score + '/5';
                document.getElementById('sentiment-pcr').textContent = (sentiment.components.pcr || 0).toFixed(3);
            }
        });
}, 1000); // Update every second
```

---

## Phase 3: Configure Environment Variables

Create/update `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/gvn_db

# Flask
SECRET_KEY=your_super_secret_key_here_min_32_chars

# Telegram Alerts
TELEGRAM_BOT_TOKEN=123456789:ABCDefGHIjKLmnoPQRstUVWxyz
TELEGRAM_CHAT_ID=-987654321

# Webhook (optional)
WEBHOOK_URL=https://your-webhook-endpoint.com/gvn-trade

# Port
PORT=8080
```

---

## Phase 4: Test Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment
export $(cat .env | xargs)

# 3. Run Flask app
python app.py

# 4. Open browser
open http://localhost:8080/user/1

# 5. Check system status
curl http://localhost:8080/api/system-status | jq
```

---

## Phase 5: Deploy to Render

### 1. Push to GitHub
```bash
git add .
git commit -m "GVN System: Complete 25-point implementation"
git push origin main
```

### 2. Connect to Render
- Create new Web Service
- Connect GitHub repo
- Set environment variables in Render dashboard
- Deploy

### 3. Verify Deployment
```bash
curl https://gvn-master-ai.onrender.com/api/system-status
```

---

## 🔄 Daily Operations

### Morning (9:15 AM)
1. System auto-calculates GVN i-levels
2. Generates 4 trade setups
3. Sends Telegram notification "🎯 Daily Setup Ready"
4. Paper trading begins simulation

### Trading Hours (9:15 AM - 3:15 PM)
1. Every 1-second tick: Update Greeks & Sentiment
2. Monitor entry conditions
3. Execute live trades (if enabled)
4. Execute parallel paper trades
5. Send Telegram alerts on entry/exit

### End of Day (3:15 PM)
1. Auto square-off all open positions
2. Calculate daily P&L
3. Send daily summary to Telegram
4. Reset daily stats

---

## 🚀 Testing Checklist

- [ ] System initializes without errors
- [ ] Dashboard loads and updates every second
- [ ] Paper trading executes sample trades
- [ ] Telegram alerts send correctly
- [ ] Greeks calculate accurately
- [ ] Sentiment changes with market
- [ ] i-Levels display correct values
- [ ] Database persists trades
- [ ] Auto square-off triggers at 3:15 PM

---

## 📞 Common Issues

**Issue:** "No module named 'gvn_greeks_engine'"
**Fix:** Make sure all `.py` files are in the same directory as `app.py`

**Issue:** Telegram alerts not sending
**Fix:** Check bot token and chat ID in .env file

**Issue:** Database connection error
**Fix:** Verify DATABASE_URL and ensure PostgreSQL is running

**Issue:** Options chain data not updating
**Fix:** Check broker API credentials and webhook connection

---

## 🎉 Success Indicators

- ✅ Dashboard shows "✅ Active" status
- ✅ Paper trading balance updates
- ✅ i-Levels update at 9:15 AM
- ✅ Telegram alerts arrive in real-time
- ✅ Live trades execute without errors
- ✅ P&L calculates correctly
- ✅ 3:15 PM auto square-off works

---

**Ready to Trade! 🚀**
