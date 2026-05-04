
import sys
import pkg_resources

print(f"Python Version: {sys.version}")
print(f"Python Path: {sys.path}")

print("\n--- INSTALLED PACKAGES ---")
installed_packages = {pkg.key for pkg in pkg_resources.working_set}
if 'smartapi-python' in installed_packages:
    print("✅ smartapi-python is installed!")
else:
    print("❌ smartapi-python is NOT found in pkg_resources.")

try:
    import SmartApi
    print("✅ Success: import SmartApi worked!")
    print(f"Module file: {SmartApi.__file__}")
except ImportError as e:
    print(f"❌ Error: import SmartApi failed: {e}")

try:
    from smartapi import SmartConnect
    print("✅ Success: from smartapi import SmartConnect worked!")
except ImportError as e:
    print(f"❌ Error: from smartapi import SmartConnect failed: {e}")
