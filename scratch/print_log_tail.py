import os

log_path = "nse_status.log"
if os.path.exists(log_path):
    print("=== LAST 50 LINES OF nse_status.log ===")
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        for line in lines[-50:]:
            print(line.strip())
else:
    print("nse_status.log not found.")
