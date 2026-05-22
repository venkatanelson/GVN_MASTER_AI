import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shared_data
import nse_option_chain

print("get_angel_token definition location:", nse_option_chain.get_angel_token)
print("find_angel_token_and_segment definition location:", nse_option_chain.find_angel_token_and_segment)

# Let's run a test call directly
token = nse_option_chain.get_angel_token()
print("Token:", token)
t_id, seg = nse_option_chain.find_angel_token_and_segment("NIFTY", 23550, "CE")
print("Resolved Token & Seg:", t_id, seg)
