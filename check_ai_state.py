
import shared_data
import json

def check_ai_mind():
    print("--- GVN AI CURRENT MIND STATE ---")
    print(f"NIFTY Spot: {shared_data.market_data.get('NIFTY')}")
    print(f"Market Score: {shared_data.market_pulse.get('score', 'N/A')}")
    print(f"Algo Status: {shared_data.market_pulse.get('algo_status', 'OFF')}")
    print(f"Active Trades: {len(shared_data.active_trades.get('live', []))}")
    print(f"Alpha Grid Count: {len(shared_data.gvn_alpha_grid)}")
    
    if shared_data.gvn_alpha_grid:
        print("Top Strike in Grid:")
        print(json.dumps(shared_data.gvn_alpha_grid[0], indent=2))
    else:
        print("Alpha Grid is currently empty.")

if __name__ == "__main__":
    check_ai_mind()
