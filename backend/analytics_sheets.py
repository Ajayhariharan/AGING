import os
import sys
import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from parser import (
    sanitize_df, get_col_exact, sort_weeks_list,
    get_channel_filter_options, ALLOWED_BRANCHES
)
from database import CACHE, load_active_or_latest_from_sqlite

def calculate_sheet_data(sheet_name: str, filters: Dict[str, List[str]], limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    """
    Handles Sheet Data Viewer and Master Sheet pagination with custom multi-filters.
    """
    if not CACHE.get("loaded"):
        load_active_or_latest_from_sqlite()
    sheets = CACHE.get("sheets", {})
    if sheet_name not in sheets:
        return {"error": "Sheet not found"}
    
    df = sheets[sheet_name]
    is_master = 'master' in sheet_name.lower()

    week_col = get_col_exact(df, ['Week', 'week', 'WEEK', 'Wk'])
    branch_col = get_col_exact(df, ['Branch', 'branch', 'BRANCH'])
    mt_col = get_col_exact(df, ['MT', 'mt', 'Channel', 'channel'])
    bucket_col = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %'])
    material_col = get_col_exact(df, ['Material Code', 'Material code', 'MATERIAL CODE', 'Material'])
    stock_col = get_col_exact(df, ['Total Stock in Case', 'Total stock in case', 'Stock'])
    cr_col = get_col_exact(df, ['Cr', 'CR', 'cr', 'Value'])

    if is_master:
        filter_candidates = ['Depot', 'Material code', 'Category', 'Depot Description', 'Base code Des.', 'Iop Category']
    else:
        filter_candidates = [c for c in [week_col, branch_col, mt_col, bucket_col] if c]

    available_filter_options = {}
    for col in filter_candidates:
        if col in df.columns:
            if col == week_col:
                raw_unique = sort_weeks_list(df[col].dropna().unique())
            else:
                raw_unique = sorted(set(str(x) for x in df[col].dropna().unique() if str(x).strip() != ''))
                if col == branch_col:
                    raw_unique = [v for v in raw_unique if v in ALLOWED_BRANCHES]
                elif col == mt_col:
                    raw_unique = get_channel_filter_options(raw_unique)
                elif col == bucket_col:
                    base_buckets = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75']
                    display_opts = [b for b in base_buckets if b in raw_unique]
                    display_opts.append('>75%')
                    raw_unique = display_opts
            available_filter_options[col] = raw_unique

    filtered_df = df
    if filters:
        for col, selected in filters.items():
            if selected and col in filtered_df.columns:
                if col == bucket_col:
                    expanded = []
                    raw_all = df[col].dropna().unique().tolist()
                    for item in selected:
                        if item == '>75%':
                            expanded.extend([b for b in raw_all if str(b).strip() in ['75 to 80', '80 to 85']])
                        else:
                            expanded.append(item)
                    if expanded:
                        filtered_df = filtered_df[filtered_df[col].astype(str).isin(expanded)]
                else:
                    filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)]

    if is_master:
        kpis = {
            "rows": len(filtered_df),
            "unique_materials": filtered_df[material_col].nunique() if material_col else 0,
            "unique_depots": filtered_df['Depot'].nunique() if 'Depot' in filtered_df.columns else 0,
            "unique_categories": filtered_df['Category'].nunique() if 'Category' in filtered_df.columns else 0
        }
    else:
        num_cr = pd.to_numeric(filtered_df[cr_col], errors='coerce').fillna(0) if cr_col else pd.Series([0])
        num_stk = pd.to_numeric(filtered_df[stock_col], errors='coerce').fillna(0) if stock_col else pd.Series([0])
        kpis = {
            "rows": len(filtered_df),
            "total_stock": int(num_stk.sum()),
            "amount_crores": round(float(num_cr.sum()), 2),
            "skus": filtered_df[material_col].nunique() if material_col else 0
        }

    display_df = filtered_df
    if is_master:
        target_base_names = [
            'Material code', 'SKU Des', 'Link Code', 'Base Code', 'Base code Des.',
            'Category', 'Iop Category', 'Line SKU', 'Base Code', 'Material code',
            'Weight per CSE', 'IOP Cat', 'Total Shelf life', 'Chn'
        ]
        selected_cols = []
        used_cols = set()
        for base in target_base_names:
            if base in display_df.columns and base not in used_cols:
                selected_cols.append(base)
                used_cols.add(base)
            else:
                for col in display_df.columns:
                    if col not in used_cols and col.startswith(base + '_'):
                        selected_cols.append(col)
                        used_cols.add(col)
                        break
        if selected_cols:
            display_df = display_df[selected_cols]

    total_rows = len(display_df)
    sliced_df = display_df.iloc[offset : offset + limit]
    
    records = []
    for _, row in sliced_df.iterrows():
        record = {}
        for c in display_df.columns:
            val = row[c]
            if pd.isna(val) or val is None:
                record[c] = ""
            elif isinstance(val, float):
                record[c] = round(val, 4) if ('cr' in c.lower() or 'value' in c.lower()) else round(val, 2)
            else:
                record[c] = str(val)
        records.append(record)

    return {
        "kpis": kpis,
        "is_master": is_master,
        "filter_options": available_filter_options,
        "columns": list(display_df.columns),
        "total_rows": total_rows,
        "data": records
    }

