<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GVN Algo - Subscription Plans</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; text-align: center; }
        .header { background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .plans-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .plan-card { background: #fff; border-radius: 10px; padding: 30px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-top: 5px solid #1a73e8; display: flex; flex-direction: column; justify-content: space-between;}
        .premium { border-top-color: #ff9800; transform: scale(1.05); }
        .ultimate { border-top-color: #dc3545; }
        .price { font-size: 32px; font-weight: bold; color: #333; margin: 15px 0; }
        .features { list-style: none; padding: 0; text-align: left; }
        .features li { padding: 10px 0; border-bottom: 1px solid #eee; color: #555; }
        .btn-buy { background: #28a745; color: white; border: none; padding: 12px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; text-decoration: none; display: block; margin-top: 20px; }
        .btn-buy:hover { background: #218838; }
        .back-btn { display: inline-block; margin-top: 30px; color: #1a73e8; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>🚀 Upgrade to Real Money Trading</h1>
        <p>Choose the best algorithmic plan to automate your trades securely via Dhan API. Contact Admin to activate.</p>
    </div>

    <div class="plans-grid">
        <!-- Basic Plan -->
        <div class="plan-card">
            <div>
                <h2>Basic Plan</h2>
                <div class="price">₹ 2,999<span style="font-size:16px;color:#888;">/mo</span></div>
                <ul class="features">
                    <li>✅ BankNifty / Nifty Signals</li>
                    <li>✅ 1 Lot Automation</li>
                    <li>✅ Basic Support</li>
                    <li>❌ Trailing SL</li>
                </ul>
            </div>
            <a href="https://wa.me/919966123078?text=Hello%20Admin,%20I%20want%20to%20upgrade%20to%20the%20Basic%20Plan%20for%20Real%20Trading." target="_blank" class="btn-buy">Contact on WhatsApp</a>
        </div>

        <!-- Premium Plan -->
        <div class="plan-card premium">
            <div style="background:#fff3cd; padding:5px; border-radius:15px; font-weight:bold; color:#856404; font-size:12px; display:inline-block; margin-bottom:10px;">🔥 MOST POPULAR</div>
            <div>
                <h2>Premium Plan</h2>
                <div class="price">₹ 5,999<span style="font-size:16px;color:#888;">/mo</span></div>
                <ul class="features">
                    <li>✅ All Basic Features</li>
                    <li>✅ Upto 5 Lots Automation</li>
                    <li>✅ Priority Support</li>
                    <li>✅ Advanced Trailing SL</li>
                </ul>
            </div>
            <a href="https://wa.me/919966123078?text=Hello%20Admin,%20I%20want%20to%20upgrade%20to%20the%20Premium%20Plan%20for%20Real%20Trading." target="_blank" class="btn-buy" style="background:#ff9800;">Contact on WhatsApp</a>
        </div>

        <!-- Ultimate Plan -->
        <div class="plan-card ultimate">
            <div>
                <h2>Ultimate Plan</h2>
                <div class="price">₹ 9,999<span style="font-size:16px;color:#888;">/mo</span></div>
                <ul class="features">
                    <li>✅ Premium Features</li>
                    <li>✅ Unlimited Lots</li>
                    <li>✅ 24/7 Dedicated Server</li>
                    <li>✅ Custom Strategies</li>
                </ul>
            </div>
            <a href="https://wa.me/919966123078?text=Hello%20Admin,%20I%20want%20to%20upgrade%20to%20the%20Ultimate%20Plan%20for%20Real%20Trading." target="_blank" class="btn-buy" style="background:#dc3545;">Contact on WhatsApp</a>
        </div>
    </div>

    <a href="/" class="back-btn">← Back to Dashboard</a>
</div>

</body>
</html>
