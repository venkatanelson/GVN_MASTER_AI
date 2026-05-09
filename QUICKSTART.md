# GVN Trading System - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Verify Installation
```bash
python gvn_integration_test.py
```
✅ Should show: "ALL TESTS PASSED"

### Step 2: Configure Broker (Optional)
Edit your broker credentials in `.env`:
```
BROKER=dhan
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_token
SHOONYA_CLIENT_ID=your_client
SHOONYA_PASSWORD=your_pwd
```

### Step 3: Start Trading
```python
from gvn_startup import start_trading, stop_trading, get_system_status

# Start the system
start_trading()

# Monitor in real-time
import time
while True:
    status = get_system_status()
    print(f"Active Trades: {status['robot_active_trades']}")
    print(f"Total P&L: {status['trading_stats']['total_pnl']}")
    time.sleep(5)
```

### Step 4: Stop Trading
```python
stop_trading()
```

---

## 📊 Real-Time Monitoring

### Check System Status
```python
from gvn_startup import get_system_status

status = get_system_status()

print("System Status:")
print(f"  Running: {status['system_running']}")
print(f"  Uptime: {status['uptime_minutes']:.1f} minutes")
print(f"  Active Trades: {status['robot_active_trades']}")
print(f"  Total Trades: {status['trading_stats']['total_trades']}")
print(f"  Winning Trades: {status['trading_stats']['winning_trades']}")
print(f"  Total P&L: {status['trading_stats']['total_pnl']:.2f}")
print(f"  Order Success Rate: {status['broker_stats']['success_rate']:.1f}%")
```

### View Security Audit Log
```python
from security_engine_v2 import SecurityShield

shield = SecurityShield()
logs = shield.get_audit_log(limit=20)

for event in logs:
    print(f"{event['timestamp']} | {event['event_type']} | {event['ip']} | {event['description']}")
```

---

## 🎯 Understanding the Trading Flow

```
9:15 AM Market Open
    ↓
Robot captures 9:15 candle (High/Low)
    ↓
Calculate GVN Levels (i0-i7)
    ↓
Monitor real-time price (every 1 second)
    ↓
Identify Delta 0.59-0.69 strikes
    ↓
Price touches level ± 0.25 pts
    ↓
EXECUTE TRADE (Market Order)
    ↓
Track position until:
  • SL Hit (-12 pts)
  • Target Hit (i2/i3/i5)
  • Panic Exit (-16 pts)
    ↓
Exit & Log Trade
    ↓
Repeat next opportunity
```

---

## 🔧 Key Configuration

### Trading Parameters
```python
# In gvn_master_robot.py
priority_delta_min = 0.59
priority_delta_max = 0.69
stop_loss_pts = 12
panic_exit_pts = 16
```

### Market Hours
- **Open**: 9:15 AM IST
- **Close**: 3:30 PM IST
- **Days**: Monday - Friday only

### Level Tolerance
- **Entry Detection**: ±0.25 points
- **If price is within 0.25 of a level = ENTRY TRIGGER**

---

## 📈 Performance Tracking

### Daily P&L
```python
from shared_data import get_trade_stats

stats = get_trade_stats()
daily_pnl = stats['total_pnl']
win_rate = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0

print(f"Today's P&L: {daily_pnl:.2f}")
print(f"Win Rate: {win_rate:.1f}%")
```

### Order Execution Stats
```python
from broker_api import get_order_stats

stats = get_order_stats()
print(f"Orders Placed: {stats['total']}")
print(f"Successful: {stats['successful']}")
print(f"Success Rate: {stats['success_rate']:.1f}%")
```

---

## 🚨 Common Issues & Solutions

### Issue: "No priority strikes found"
- **Cause**: Option chain hasn't loaded yet
- **Solution**: Wait until 9:20 AM, ensure broker is connected
- **Check**: Verify nse_option_chain.py is pulling data

### Issue: "Orders not executing"
- **Cause**: Broker connection issue
- **Solution**: Verify .env credentials, restart system
- **Check**: `broker_api.dhan_http_test()` or `broker_api.shoonya_http_login()`

### Issue: "System stopped suddenly"
- **Cause**: Unhandled exception
- **Solution**: Check logs, restart with debug mode
- **Log File**: Check console output or `security_audit_log.json`

### Issue: "High error count"
- **Cause**: Market volatility or data lag
- **Solution**: Enable attack mode for stricter rate limits
- **Code**: `shield.enable_attack_mode()`

---

## 🛡️ Security Checklist

- [ ] File integrity locked at startup
- [ ] Audit log being saved (`security_audit_log.json`)
- [ ] IP whitelist configured
- [ ] Telegram alerts enabled (optional)
- [ ] Attack mode disabled (unless needed)
- [ ] .env file not committed to git

---

## 📊 Supported Indices

✅ NIFTY 50 (Lot: 65)
✅ BANKNIFTY (Lot: 40)
✅ FINNIFTY (Lot: 75)

---

## 🔗 Integration Examples

### With Flask Web App
```python
from flask import Flask, jsonify
from gvn_startup import get_system_status

app = Flask(__name__)

@app.route('/api/status')
def status():
    return jsonify(get_system_status())

if __name__ == '__main__':
    app.run(port=5000)
```

### With Telegram Bot
```python
def send_alert(message):
    # Implement Telegram notification
    pass

# Pass to startup
from gvn_startup import GVNSystem
system = GVNSystem()
system.robot.telegram_alert = send_alert
```

### Multi-Index Monitoring
```python
status = get_system_status()

for index in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
    market_data = status['market_data'][index]
    print(f"{index}: {market_data['spot']}")
```

---

## 📞 Troubleshooting

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Individual Components
```bash
# Test all components
python gvn_integration_test.py

# Test broker connection
python -c "from broker_api import dhan_http_test; print(dhan_http_test({}))"

# Test level calculations
python -c "from gvn_levels_engine import calculate_gvn_levels; print(calculate_gvn_levels(100, 90))"
```

---

## 📝 Next Steps

1. **Run Integration Tests**: Verify all components work
2. **Configure Broker**: Add credentials to .env
3. **Start in Paper Trading**: Use test broker account
4. **Monitor Closely**: First week should be watched carefully
5. **Optimize Settings**: Adjust based on market conditions

---

## 📞 Support Resources

- **Configuration**: See `GVN_UPDATE_2026.md`
- **API Reference**: Check individual module docstrings
- **Security**: Review `security_engine_v2.py`
- **Trading Logic**: Refer to `gvn_master_robot.py`

---

**Version**: 2.0  
**Last Updated**: 2026-04-29  
**Status**: Production Ready ✅
