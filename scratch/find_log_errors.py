import sys

sys.stdout.reconfigure(encoding='utf-8')

def find_errors():
    try:
        with open("nse_status.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        print("=== LOG ANALYSIS FOR ERRORS/WARNINGS ===")
        err_lines = [l for l in lines if any(w in l.upper() for w in ["ERR", "FAIL", "WARN", "EXCEPT", "BLOCK", "OFFLINE"])]
        print(f"Total error/warning lines: {len(err_lines)}")
        
        print("\nLast 20 error/warning lines:")
        for l in err_lines[-20:]:
            print(l.strip())
            
        print("\n=== CHECKS FOR ANGEL/SHOONYA ===")
        broker_lines = [l for l in lines if any(w in l.upper() for w in ["ANGEL", "SHOONYA", "DHAN", "TRUEDATA"])]
        print(f"Total broker-related lines: {len(broker_lines)}")
        for l in broker_lines[-20:]:
            print(l.strip())
            
    except Exception as e:
        print("Error reading log:", e)

if __name__ == "__main__":
    find_errors()
