def calculate_gvn_levels(high915, low915):
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    levels = {
        "i1 (GVN Top)": round(gvn100, 2),
        "i2 (Reversal Zone)": round(gvn0 + 0.763 * gvnR, 2),
        "i3 (Bullish Breakout)": round(gvn0 + 0.618 * gvnR, 2),
        "i5 (Pivot)": round(gvn0 + 0.500 * gvnR, 2),
        "i6 (Golden Zone)": round(gvn0 + 0.382 * gvnR, 2),
        "i7 (ITM/ATM Support)": round(gvn0 + 0.220 * gvnR, 2),
        "i0 (GVN Bottom)": round(gvn0, 2)
    }
    
    for k, v in levels.items():
        print(f"{k}: ₹{v}")

print("For 24200 CE (High: 229.50, Low: 149.50):")
calculate_gvn_levels(229.50, 149.50)

print("\nWait, did he say 229.50 or 229.00?")
print("For 24200 CE (High: 229.00, Low: 149.50):")
calculate_gvn_levels(229.00, 149.50)
