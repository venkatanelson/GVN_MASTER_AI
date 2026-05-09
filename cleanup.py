import os
import shutil

unnecessary_files = [
    'dhan_live_feed.py', 'check_dhan.py', 'test_dhan_api.py', 'test_dhan_auth.py', 
    'test_dhan_direct.py', 'dhan_feed_status.log', 'inspect_dhan.py',
    'test_all_brokers.py', 'test_app.py', 'test_auto_pilot.py', 'test_brokers_live.py', 
    'test_login.py', 'test_mcx_data.py', 'test_nse.py', 'test_raw.py', 'test_webhook.py', 
    'test_truedata_login.py', 'test_truedata_rest.py',
    'check_db.py', 'check_schema.py', 'check_status.py', 'check_imports.py',
    'fix_db.py', 'fix_db2.py', 'fix_schema.py',
    'repair_app.py', 'repair_db_render.py', 'repair_gvn.py',
    'recover_keys.py', 'peek_keys.py', 'temp_save_pwd.py',
    'migrate_db.py', 'reset_database.py',
    'db_report.txt', 'test_output.txt'
]

print("🗑️ Starting GVN Cleanup...")
for f in unnecessary_files:
    if os.path.exists(f):
        try:
            os.remove(f)
            print(f"✅ Removed: {f}")
        except Exception as e:
            print(f"❌ Failed to remove {f}: {e}")
    else:
        print(f"⏭️ Skipped (Not found): {f}")

print("\n🚀 Cleanup Complete! System is now lightweight.")
