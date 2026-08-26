import os
import sys
import sqlite3
import pandas as pd

db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'inventory.db')
conn = sqlite3.connect(db_path)

# File 1: JUNE
df_june = pd.read_sql("SELECT * FROM f_1_Curr_stock_2", conn)
cr_col1 = 'Cr'
df_june[cr_col1] = pd.to_numeric(df_june[cr_col1], errors='coerce').fillna(0)

# File 3: JULY (3rd July)
df_july = pd.read_sql("SELECT * FROM f_3_Curr_stock_2", conn)
cr_col3 = 'Cr'
df_july[cr_col3] = pd.to_numeric(df_july[cr_col3], errors='coerce').fillna(0)

print("=== JUNE SUMMARY ===")
print("Total rows:", len(df_june))
print("Total Value (Cr):", df_june[cr_col1].sum())
print("Weeks in June:", df_june['Week'].unique())

print("\n=== JULY SUMMARY (3rd July) ===")
print("Total rows:", len(df_july))
print("Total Value (Cr):", df_july[cr_col3].sum())
print("Weeks in July:", df_july['Week'].unique())

print("\n=== CATEGORY COMPARISON JUNE VS JULY ===")
cat_col_june = [c for c in df_june.columns if 'local category' in c.lower()][0]
cat_col_july = [c for c in df_july.columns if 'local category' in c.lower()][0]

june_cat = df_june.groupby(cat_col_june)[cr_col1].sum()
july_cat = df_july.groupby(cat_col_july)[cr_col3].sum()

comp = pd.DataFrame({'June': june_cat, 'July (Wk 1)': july_cat}).fillna(0)
comp['Net Change (Cr)'] = comp['July (Wk 1)'] - comp['June']
comp['Growth %'] = ((comp['Net Change (Cr)'] / comp['June']) * 100).round(1).astype(str) + '%'
print(comp)

