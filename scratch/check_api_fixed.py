import requests
import json
import sys

# Set output encoding to UTF-8 for Windows console
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ports = [8080, 5000, 8000, 5001]
success = False

for port in ports:
    url = f"http://127.0.0.1:{port}/api/user-status"
    try:
        print(f"Trying port {port}...")
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            print(f"✅ Success on port {port}!")
            data = res.json()
            print(json.dumps(data, indent=2))
            
            # Now let's try broker-status
            broker_url = f"http://127.0.0.1:{port}/api/broker-status"
            try:
                bres = requests.get(broker_url, timeout=2)
                if bres.status_code == 200:
                    print("\n--- Broker Status ---")
                    print(json.dumps(bres.json(), indent=2))
            except Exception as e:
                print(f"Failed to get broker status: {e}")
                
            # Now let's try ai-memory
            aimem_url = f"http://127.0.0.1:{port}/api/ai-memory"
            try:
                mres = requests.get(aimem_url, timeout=2)
                if mres.status_code == 200:
                    print("\n--- AI Memory / Evening Report ---")
                    mdata = mres.json()
                    print(f"Total Observations: {mdata.get('total_observations')}")
                    print("Evening Report:")
                    print(mdata.get('evening_report'))
            except Exception as e:
                print(f"Failed to get AI memory: {e}")
                
            success = True
            break
    except Exception as e:
        print(f"Failed on port {port}: {e}")

if not success:
    print("Could not connect to Flask app on any standard port.")
