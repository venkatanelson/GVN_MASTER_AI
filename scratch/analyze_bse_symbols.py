import pandas as pd

df = pd.read_csv(r"c:\Users\Gvn\OneDrive\Desktop\my_algo_project\indian_all_stocks_5000.csv")

bse_df = df[df['Exchange'] == 'BSE']
bse_letters = bse_df[bse_df['Symbol'].str[0].str.isalpha() == True]
bse_digits = bse_df[bse_df['Symbol'].str[0].str.isdigit() == True]

print("BSE symbols starting with letter:", len(bse_letters))
print("BSE symbols starting with digit:", len(bse_digits))

print("\nSample BSE symbols starting with letter:")
print(bse_letters.head(30))

print("\nSample BSE symbols starting with digit:")
print(bse_digits.head(30))
