from dhanhq import dhanhq
import inspect

dhan = dhanhq("dummy", "dummy")
methods = [m for m in dir(dhan) if not m.startswith('_')]
print("Available Methods in dhanhq object:")
for m in methods:
    print(f" - {m}")
