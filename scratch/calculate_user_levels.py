def calculate_gvn_levels(high915, low915):
    diff = high915 - low915
    result = diff / 2
    n1 = high915 + result
    n2 = low915 + result
    
    gvn0 = n2 * 0.118 / 0.5
    gvn100 = n1 * 0.786 / 0.5
    gvnR = gvn100 - gvn0
    
    i2 = gvn0 + 0.763 * gvnR
    i3 = gvn0 + 0.618 * gvnR
    i5 = gvn0 + 0.500 * gvnR
    i6 = gvn0 + 0.382 * gvnR
    i7 = gvn0 + 0.220 * gvnR
    
    return {
        "i1": round(gvn100, 6),
        "i0": round(gvn0, 6),
        "i2": round(i2, 6),
        "i3": round(i3, 6),
        "i5": round(i5, 6),
        "i6": round(i6, 6),
        "i7": round(i7, 6)
    }

if __name__ == "__main__":
    levels = calculate_gvn_levels(364.75, 320.10)
    print("For High=364.75, Low=320.10:")
    for k, v in levels.items():
        print(f"  {k}: {v}")
