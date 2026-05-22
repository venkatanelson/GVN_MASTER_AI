import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nse_option_chain import calculate_gvn_levels

def main():
    print("================ GVN LEVEL VERIFICATION ================")
    
    # Test case 1: NIFTY 23650 CE
    # High: 205.65, Low: 174.40
    print("\n[Test Case 1] NIFTY 23650 CE")
    print("Coordinates: High = 205.65, Low = 174.40")
    levels_23650 = calculate_gvn_levels(205.65, 174.40)
    print(f"Calculated i5 (1st Entry): {levels_23650['i5']} (Expected: ~196.35)")
    print(f"Calculated i7 (2nd Entry): {levels_23650['i7']} (Expected: ~111.51)")
    
    # Test case 2: NIFTY 23400 CE
    # High: 382.10, Low: 340.00
    print("\n[Test Case 2] NIFTY 23400 CE")
    print("Coordinates: High = 382.10, Low = 340.00")
    levels_23400 = calculate_gvn_levels(382.10, 340.00)
    print(f"Calculated i5 (1st Entry): {levels_23400['i5']} (Expected: ~359.48)")
    print(f"Calculated i7 (2nd Entry): {levels_23400['i7']} (Expected: ~205.89)")
    
    print("\n========================================================")

if __name__ == "__main__":
    main()
