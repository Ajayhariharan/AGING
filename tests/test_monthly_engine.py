import os
import sys
import sqlite3
import re
import pandas as pd
import numpy as np

db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'inventory.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, filename, stock_sheet_name, sheet_names FROM _files_history ORDER BY id ASC")
files = cursor.fetchall()

def get_month_display_name(filename, file_id, df):
    f_lower = filename.lower()
    months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
              'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    found_month = None
    for m in months:
        if m in f_lower:
            found_month = m.capitalize()[:3]
            break
    if not found_month:
        found_month = f"File {file_id}"
    
    # Check weeks in df
    week_col = None
    for c in df.columns:
        if 'week' in c.lower() or 'wk' in c.lower():
            week_col = c
            break
    if week_col:
        u_w = [str(x) for x in df[week_col].dropna().unique() if str(x).strip() != '' and str(x).lower() not in ['nan', 'none']]
        if len(u_w) == 1:
            return f"{found_month} ({u_w[0]})"
        elif len(u_w) > 1:
            return f"{found_month} (Wk 1-{len(u_w)})"
    return found_month

monthly_dfs = {}
for f in files:
    f_id, f_name, stock_sheet, sheet_names_str = f
    sheet_list = sheet_names_str.split(',') if sheet_names_str else []
    target_sheet = stock_sheet or (sheet_list[1] if len(sheet_list) > 1 else sheet_list[0])
    clean_sheet = re.sub(r'[^a-zA-Z0-9_]', '_', target_sheet.strip())
    table_name = f"f_{f_id}_{clean_sheet}"
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        label = get_month_display_name(f_name, f_id, df)
        monthly_dfs[label] = df
        print(f"Loaded {label} from table {table_name}, rows={len(df)}")
    except Exception as e:
        print(f"Error loading {table_name}: {e}")

print("Monthly labels:", list(monthly_dfs.keys()))

