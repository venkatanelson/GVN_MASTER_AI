import pandas as pd

df = pd.read_csv(r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\indian_all_stocks_5000.csv")
print("Total rows:", len(df))
print("First 30 rows:")
print(df.head(30))
print("\nUnique Exchange values counts:")
print(df['Exchange'].value_counts())
