import pandas as pd
import os

csv_path = r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\gvn_filtered_stocks.csv"
xlsx_path = r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\gvn_filtered_stocks.xlsx"

try:
    df = pd.read_csv(csv_path)
    # Check if openpyxl is installed by attempting to write
    df.to_excel(xlsx_path, index=False)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
