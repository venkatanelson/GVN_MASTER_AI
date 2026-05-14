import hashlib
import os

files = ["app.py", "nse_option_chain.py", "truedata_ws_connector.py", "security_engine_v2.py"]
for f in files:
    if os.path.exists(f):
        with open(f, "rb") as file:
            print(f"{f}: {hashlib.sha256(file.read()).hexdigest()}")
