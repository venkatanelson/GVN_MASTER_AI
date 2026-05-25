# Let's search for high and low values that produce the exact levels:
# 2nd Entry = 88.701792
# Target 1 = 130.4189952
# Target 2 = 160.8056

# Standard level definitions:
# levels["i1"] = gvn0
# levels["i7"] = gvn0 + 0.220 * spread
# levels["i6"] = gvn0 + 0.382 * spread
# levels["i5"] = gvn0 + 0.500 * spread
# levels["i3"] = gvn0 + 0.618 * spread
# levels["i2"] = gvn0 + 0.763 * spread
# levels["i0"] = gvn_i1

# Let's check which levels B and C can be.
# If C is Target 2 and B is Target 1:
# Let's search all level pairs (A_name, B_name, C_name) and find (high, low) that match.

def check_match(high, low):
    diff = high - low
    res = diff / 2
    n1 = high + res
    n2 = low + res
    gvn0 = n2 * 0.236
    gvn_i1 = n1 * 1.572
    spread = gvn_i1 - gvn0
    
    levels = {
        "i1": gvn0,
        "i7": gvn0 + 0.220 * spread,
        "i6": gvn0 + 0.382 * spread,
        "i5": gvn0 + 0.500 * spread,
        "i3": gvn0 + 0.618 * spread,
        "i2": gvn0 + 0.763 * spread,
        "i0": gvn_i1,
    }
    return levels

target_A = 88.701792
target_B = 130.4189952
target_C = 160.8056

# Loop over possible level names
lvl_names = ["i1", "i7", "i6", "i5", "i3", "i2", "i0"]

found = False
for a in lvl_names:
    for b in lvl_names:
        for c in lvl_names:
            if a == b or b == c or a == c:
                continue
            # Solve for gvn0 and spread:
            # Let's say:
            # gvn0 + R_a * spread = target_A
            # gvn0 + R_b * spread = target_B
            # (R_b - R_a) * spread = target_B - target_A
            # spread = (target_B - target_A) / (R_b - R_a)
            # gvn0 = target_A - R_a * spread
            
            # Map names to ratios
            ratios = {
                "i1": 0.0,
                "i7": 0.220,
                "i6": 0.382,
                "i5": 0.500,
                "i3": 0.618,
                "i2": 0.763,
                "i0": 1.0
            }
            
            ra = ratios[a]
            rb = ratios[b]
            rc = ratios[c]
            
            if rb == ra or rc == rb:
                continue
                
            spread = (target_B - target_A) / (rb - ra)
            gvn0 = target_A - ra * spread
            
            # check if C matches
            val_c = gvn0 + rc * spread
            if abs(val_c - target_C) < 0.001:
                # This combination matches!
                # Now find high and low from gvn0 and spread:
                # gvn_i1 = gvn0 + spread
                # gvn0 = (low + (high - low)/2) * 0.236 = (low + high) * 0.118
                # gvn_i1 = (high + (high - low)/2) * 1.572 = (3*high - low) * 0.786
                # So we have system of equations:
                # 1) (high + low) * 0.118 = gvn0
                # 2) (3*high - low) * 0.786 = gvn_i1
                
                # From 1: high + low = gvn0 / 0.118
                # From 2: 3*high - low = gvn_i1 / 0.786
                # Adding 1 and 2: 4*high = gvn0/0.118 + gvn_i1/0.786
                # high = (gvn0/0.118 + gvn_i1/0.786) / 4
                # low = gvn0/0.118 - high
                
                gvn_i1 = gvn0 + spread
                high = (gvn0 / 0.118 + gvn_i1 / 0.786) / 4
                low = (gvn0 / 0.118) - high
                
                print(f"MATCH: Entry={a}, Target1={b}, Target2={c}")
                print(f"Calculated: High={high:.2f}, Low={low:.2f}")
                print(f"gvn0={gvn0:.4f}, spread={spread:.4f}")
                print(f"Levels: {check_match(high, low)}")
                found = True

if not found:
    print("No level combinations match exactly with standard ratios.")
