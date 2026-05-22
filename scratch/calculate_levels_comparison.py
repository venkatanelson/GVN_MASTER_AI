def calculate_gvn_levels(high915, low915):
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    levels = {
        "i1": round(gvn100, 2),
        "i0": round(gvn0, 2),
        "i2": round(gvn0 + 0.763 * gvnR, 2),
        "i3": round(gvn0 + 0.618 * gvnR, 2),
        "i5": round(gvn0 + 0.500 * gvnR, 2),
        "i6": round(gvn0 + 0.382 * gvnR, 2),
        "i7": round(gvn0 + 0.220 * gvnR, 2)
    }
    return levels

def run_comparison():
    print("=== SCENARIO A: STALE VALUES (High=179.3, Low=107.0) ===")
    levels_stale = calculate_gvn_levels(179.3, 107.0)
    for k in ["i1", "i2", "i3", "i5", "i6", "i7", "i0"]:
        print(f"  {k}: {levels_stale[k]}")
            
    print("\n=== SCENARIO B: CORRECT TRADINGVIEW VALUES (High=364.75, Low=183.55) ===")
    levels_correct = calculate_gvn_levels(364.75, 183.55)
    for k in ["i1", "i2", "i3", "i5", "i6", "i7", "i0"]:
        print(f"  {k}: {levels_correct[k]}")

if __name__ == "__main__":
    run_comparison()
