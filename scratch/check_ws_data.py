import shared_data
import time

print("Checking shared_data.truedata_option_chains...")
for i in range(5):
    chains = shared_data.truedata_option_chains
    print(f"Attempt {i+1}: Active Chains - {list(chains.keys())}")
    if chains:
        for sym, data in chains.items():
            print(f"  - {sym}: {len(data)} strikes found")
    time.sleep(1)
