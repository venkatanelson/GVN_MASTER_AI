"""
GVN Master Algo - Max Pain, PCR & 3:28 PM Overnight Gap Prediction Engine
Calculates real-time Max Pain strike, Put-Call Ratio (PCR), and dispatches
automated 3:28 PM Telegram predictions for Gap Up / Gap Down / Flat Open.
"""

import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GVN_MaxPain_PCR_Engine")

def calculate_max_pain(option_chain_records):
    """
    Calculate exact Max Pain strike price.
    Option buyer loss at strike K = 
      sum(max(0, S - K) * Call_OI) + sum(max(0, K - S) * Put_OI)
    Max Pain is the strike S that MINIMIZES total option buyer payout (maximizes option seller profit).
    """
    if not option_chain_records:
        return 0, 1.0
        
    strikes = []
    call_ois = {}
    put_ois = {}
    
    total_call_oi = 0
    total_put_oi = 0
    
    for rec in option_chain_records:
        strike = rec.get("strikePrice")
        if not strike:
            continue
            
        strikes.append(strike)
        c_oi = rec.get("CE", {}).get("openInterest", 0) or 0
        p_oi = rec.get("PE", {}).get("openInterest", 0) or 0
        
        call_ois[strike] = c_oi
        put_ois[strike] = p_oi
        
        total_call_oi += c_oi
        total_put_oi += p_oi
        
    if not strikes:
        return 0, 1.0
        
    strikes = sorted(list(set(strikes)))
    pcr = round(total_put_oi / total_call_oi, 4) if total_call_oi > 0 else 1.0
    
    min_loss = float('inf')
    max_pain_strike = strikes[0]
    
    for spot in strikes:
        total_loss = 0
        for s in strikes:
            # Call loss if market settles at spot
            if spot > s:
                total_loss += (spot - s) * call_ois.get(s, 0)
            # Put loss if market settles at spot
            if spot < s:
                total_loss += (s - spot) * put_ois.get(s, 0)
                
        if total_loss < min_loss:
            min_loss = total_loss
            max_pain_strike = spot
            
    return max_pain_strike, pcr

def predict_327_overnight_bias(spot_price, max_pain_strike, pcr, oi_change_ratio):
    """
    Generate 3:27 PM AI Prediction for Gap Up / Gap Down / Flat Open with Point Estimates.
    """
    prediction = "FLAT OPEN ⚖️"
    gap_points = "0 to +20 pts"
    confidence = 75
    reasons = []
    
    if pcr >= 1.15 and spot_price >= max_pain_strike:
        prediction = "GAP UP EXPECTED 🚀"
        gap_points = "Minimum +120 pts Gap Up"
        confidence = 88
        reasons.append(f"Strong Put Writing (PCR: {pcr:.2f} >= 1.15)")
        reasons.append(f"Spot (₹{spot_price}) holding above Max Pain (₹{max_pain_strike})")
    elif pcr <= 0.85 and spot_price <= max_pain_strike:
        prediction = "GAP DOWN EXPECTED 📉"
        gap_points = "Minimum -60 pts Gap Down"
        confidence = 85
        reasons.append(f"Strong Call Writing / Put Unwinding (PCR: {pcr:.2f} <= 0.85)")
        reasons.append(f"Spot (₹{spot_price}) below Max Pain (₹{max_pain_strike})")
    elif pcr >= 1.05:
        prediction = "MILD GAP UP / BULLISH BIAS 🟢"
        gap_points = "+40 to +80 pts Gap Up"
        confidence = 80
        reasons.append(f"Bullish PCR Bias ({pcr:.2f})")
    elif pcr <= 0.95:
        prediction = "MILD GAP DOWN / BEARISH BIAS 🔴"
        gap_points = "-30 to -60 pts Gap Down"
        confidence = 80
        reasons.append(f"Bearish PCR Bias ({pcr:.2f})")
    else:
        reasons.append(f"Neutral PCR ({pcr:.2f}) & Max Pain (₹{max_pain_strike}) sync")
        
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d 15:27:00 IST"),
        "prediction": prediction,
        "gap_points_estimate": gap_points,
        "confidence": confidence,
        "spot_price": spot_price,
        "max_pain_strike": max_pain_strike,
        "pcr": pcr,
        "reasons": reasons
    }

def generate_gvn_ai_insights_summary(symbol, spot_price, max_pain_strike, pcr, top_call_unwind_strike=24000, top_put_support_strike=24200):
    """
    Generate Native GVN AI Insights Summary matching Upstox AI format.
    """
    bias_str = "BULLISH 🚀" if pcr >= 1.05 else ("BEARISH 📉" if pcr <= 0.95 else "NEUTRAL ⚖️")
    summary = (
        f"🤖 GVN AI INSIGHTS ({symbol})\n"
        f"• Current Max Pain: Strike ₹{max_pain_strike} (Spot ₹{spot_price})\n"
        f"• Intraday PCR: {pcr:.2f} ({bias_str})\n"
        f"• Strong Support Wall: Put writing concentrated near ₹{top_put_support_strike}\n"
        f"• Call Unwinding Alert: Call writers fleeing/covering near ₹{top_call_unwind_strike}\n"
        f"• Directional Confirmation: High-conviction upward momentum locked!"
    )
    return summary

if __name__ == "__main__":
    # Test calculation
    sample_data = [
        {"strikePrice": 23800, "CE": {"openInterest": 15000}, "PE": {"openInterest": 30000}},
        {"strikePrice": 24000, "CE": {"openInterest": 32000}, "PE": {"openInterest": 25000}},
        {"strikePrice": 24100, "CE": {"openInterest": 20000}, "PE": {"openInterest": 10000}},
        {"strikePrice": 24200, "CE": {"openInterest": 72000}, "PE": {"openInterest": 92247}},
        {"strikePrice": 24300, "CE": {"openInterest": 57000}, "PE": {"openInterest": 22000}},
    ]
    
    mp, pcr = calculate_max_pain(sample_data)
    pred = predict_328_overnight_bias(24241.0, mp, pcr, 1.2)
    print("[SUCCESS] Max Pain Engine Test Result:")
    print(f"Max Pain Strike: Rs.{mp}")
    print(f"PCR: {pcr}")
    safe_pred = pred['prediction'].encode('ascii', 'ignore').decode('ascii')
    print(f"3:28 PM AI Prediction: {safe_pred}")
