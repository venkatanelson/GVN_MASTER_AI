
import os
import time
import shared_data
from nse_option_chain import dhan_master_config, analyze_and_update_gvn_scanner, live_option_chain_summary

def test_live_connections():
    print("--- GVN BROKER CONNECTIVITY TEST ---")
    
    # 1. Sync from DB logic (simulated)
    import sqlite3
    try:
        conn = sqlite3.connect('instance/gvn_algo_pro.db')
        cursor = conn.cursor()
        cursor.execute("SELECT broker_name, client_id FROM user_broker_config LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"[DB] Found credentials for: {row[0]} (ID: {row[1]})")
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")

    # 2. Check Shared Data Credentials
    backup = shared_data.PERMANENT_CREDENTIALS_BACKUP
    print(f"[SHARED] Backup Broker: {backup.get('broker_name')} (ID: {backup.get('client_id')})")

    # 3. Test NSE Option Chain Engine
    print("\n[NSE ENGINE] Testing NIFTY Data Fetch...")
    # Temporarily set active for test
    dhan_master_config['active'] = True
    dhan_master_config['broker_name'] = backup.get('broker_name', 'AngelOne')
    
    analyze_and_update_gvn_scanner("NIFTY")
    
    summary = live_option_chain_summary.get("NIFTY", {})
    if summary.get("spot") > 0:
        print(f"✅ SUCCESS: Nifty Spot is {summary.get('spot')}")
        print(f"✅ Data Source: {live_option_chain_summary.get('last_updated')}")
    else:
        print("❌ FAILED: No data received. Checking logs...")
        with open("nse_status.log", "r") as f:
            lines = f.readlines()
            print("Last 5 log lines:")
            for line in lines[-5:]:
                print(f"  {line.strip()}")

if __name__ == "__main__":
    test_live_connections()
