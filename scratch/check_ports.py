import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_port_8080():
    print("=== PORT 8080 LISTENER ===")
    try:
        output = subprocess.check_output("netstat -ano | findstr 8080", shell=True, text=True)
        print(output)
        
        # Extract PIDs
        pids = set()
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 5:
                pids.add(parts[-1])
                
        print(f"Active PIDs on port 8080: {pids}")
        for pid in pids:
            try:
                task_out = subprocess.check_output(f"tasklist /FI \"PID eq {pid}\"", shell=True, text=True)
                print(f"\nPID {pid} task details:")
                print(task_out)
            except Exception as te:
                print(f"Error getting task details for PID {pid}: {te}")
    except Exception as e:
        print("Error checking port 8080:", e)

if __name__ == "__main__":
    check_port_8080()
