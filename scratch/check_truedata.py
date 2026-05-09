try:
    import truedata_ws
    print("truedata-ws is installed")
    print(f"Version: {truedata_ws.__version__ if hasattr(truedata_ws, '__version__') else 'unknown'}")
except ImportError:
    print("truedata-ws is NOT installed")
