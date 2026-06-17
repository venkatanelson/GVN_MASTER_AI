import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_processes():
    print("=== RUNNING PYTHON PROCESSES ===")
    try:
        # Use tasklist to see running python processes
        output = subprocess.check_output("tasklist /FI \"IMAGENAME eq python.exe\"", shell=True, text=True)
        print(output)
    except Exception as e:
        print("Error checking processes:", e)

if __name__ == "__main__":
    check_processes()
