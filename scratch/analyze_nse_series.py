import pandas as pd

df = pd.read_csv(r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\indian_all_stocks_5000.csv")

nse_df = df[df['Exchange'] == 'NSE']
nse_eq = nse_df[nse_df['Series/Group'] == 'EQ']
print("NSE symbols with series EQ:", len(nse_eq))

# Let's print unique values of Series/Group in NSE
print("\nUnique Series/Group in NSE:")
print(nse_df['Series/Group'].value_counts())

print("\nSample NSE non-EQ symbols:")
print(nse_df[nse_df['Series/Group'] != 'EQ'].head(20))
