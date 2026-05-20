import logging
logging.basicConfig(level=logging.INFO)
import sys
sys.path.append('.')
from nse_option_chain import get_real_option_915_ohlc

res = get_real_option_915_ohlc("NIFTY", 23750, "PE")
print("RESULT FOR 23750 PE:", res)
res_ce = get_real_option_915_ohlc("NIFTY", 23650, "CE")
print("RESULT FOR 23650 CE:", res_ce)
