import os
import sys
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from parser import (
    get_col_exact, sort_weeks_list, get_bucket_lower, map_to_target_bucket,
    get_channel_filter_options, TARGET_BUCKETS, ALLOWED_BRANCHES,
    STANDARD_BRANCHES, normalize_branch_filter
)
from database import get_stock_df

def calculate_dashboard_data(weeks: List[str] = [], branches: List[str] = [], channels: List[str] = []) -> Dict[str, Any]:
    """
    Computes summary KPI cards, category breakdown, top brands, branch breakdown,
    branch-category matrix, and DC Heatmap for the Executive Cockpit Dashboard.
    """
    df = get_stock_df()
    if df is None:
        return {"error": "No stock data loaded"}

    df = df.copy()
    d_week_col = get_col_exact(df, ['Week', 'week', 'WEEK', 'Wk'])
    d_branch_col = get_col_exact(df, ['Branch', 'branch', 'BRANCH'])
    d_mt_col = get_col_exact(df, ['MT', 'mt', 'Channel', 'channel'])
    d_bucket_col = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %'])
    d_brand_col = get_col_exact(df, ['IOP', 'Brand', 'Material Description', 'brand', 'BRAND'])
    
    local_cat_cols = [c for c in df.columns if c.startswith('Local Category')]
    d_cat_col = local_cat_cols[1] if len(local_cat_cols) > 1 else get_col_exact(df, ['Local Category', 'Category', 'category', 'CATEGORY'])
    
    d_link_col = get_col_exact(df, ['link des', 'link_des', 'Link des'])
    d_cr_col = get_col_exact(df, ['Cr', 'CR', 'cr', 'Value'])
    d_depot_code_col = get_col_exact(df, ['Depot Code', 'Depot code', 'DEPOT CODE'])

    if d_cr_col:
        df[d_cr_col] = pd.to_numeric(df[d_cr_col], errors='coerce').fillna(0)

    week_vals = sort_weeks_list(df[d_week_col].dropna().unique()) if d_week_col else []
    branch_vals = STANDARD_BRANCHES
    channel_vals = get_channel_filter_options(df, d_mt_col) if d_mt_col else []

    # Apply Filters
    if d_week_col and weeks:
        df = df[df[d_week_col].astype(str).isin(weeks)]
    if d_branch_col and branches:
        df = df[df[d_branch_col].astype(str).isin(normalize_branch_filter(branches))]
    if d_mt_col and channels:
        df = df[df[d_mt_col].astype(str).isin(channels)]

    # 1. Risk Cards
    if d_bucket_col and d_cr_col:
        bucket_lower_map = {b: get_bucket_lower(b) for b in df[d_bucket_col].dropna().unique()}
        lower_series = df[d_bucket_col].map(bucket_lower_map)
        high_risk_val = float(df[(lower_series >= 20) & (lower_series < 50)][d_cr_col].sum())
        med_risk_val = float(df[(lower_series >= 50) & (lower_series < 75)][d_cr_col].sum())
    else:
        high_risk_val, med_risk_val = 0.0, 0.0

    if d_bucket_col:
        df['Target_Bucket'] = df[d_bucket_col].apply(map_to_target_bucket)
    else:
        df['Target_Bucket'] = None

    def df_to_json_table(pivot_df):
        pivot_df.columns.name = None
        records = []
        for _, row in pivot_df.iterrows():
            rec = {}
            for col in pivot_df.columns:
                val = row[col]
                if isinstance(val, (int, float)) and not pd.isna(val):
                    rec[str(col)] = round(float(val), 1)
                elif val is None or pd.isna(val):
                    rec[str(col)] = ""
                else:
                    rec[str(col)] = str(val)
            records.append(rec)
        return {
            "columns": [str(c) for c in pivot_df.columns],
            "rows": records
        }

    # 2. Table 1: AT-RISK BY CATEGORY (CR)
    category_table = {"columns": [], "rows": []}
    if d_cat_col and d_cr_col and d_bucket_col:
        cat_filtered = df[df['Target_Bucket'].notna()]
        if not cat_filtered.empty:
            cat_pivot = cat_filtered.pivot_table(index=d_cat_col, columns='Target_Bucket', values=d_cr_col, aggfunc='sum', fill_value=0)
            cat_pivot = cat_pivot.reindex(columns=TARGET_BUCKETS, fill_value=0)
            cat_pivot['Row_Total'] = cat_pivot[TARGET_BUCKETS].sum(axis=1)
            grand_cat_total = cat_pivot['Row_Total'].sum()
            if grand_cat_total > 0:
                cat_pivot['Share'] = ((cat_pivot['Row_Total'] / grand_cat_total) * 100).round(1).astype(str) + '%'
            else:
                cat_pivot['Share'] = '0%'
            cat_pivot = cat_pivot.sort_values(by='Row_Total', ascending=False).drop(columns=['Row_Total'])
            total_row = cat_pivot[TARGET_BUCKETS].sum().to_frame().T
            total_row.index = ['Total']
            total_row['Share'] = '100%'
            final_cat_pivot = pd.concat([cat_pivot, total_row]).reset_index().rename(columns={'index': 'Category', d_cat_col: 'Category'})
            category_table = df_to_json_table(final_cat_pivot)

    # 3. Table 5: AT-RISK BY BRANCH x CATEGORY (CR)
    branch_cat_table = {"columns": [], "rows": []}
    if d_branch_col and d_cat_col and d_cr_col:
        filtered_branch_df = df[df[d_branch_col].astype(str).str.strip().isin(ALLOWED_BRANCHES)]
        if not filtered_branch_df.empty:
            branch_cat_pivot = filtered_branch_df.pivot_table(index=d_branch_col, columns=d_cat_col, values=d_cr_col, aggfunc='sum', fill_value=0)
            branch_cat_pivot['Total'] = branch_cat_pivot.sum(axis=1)
            total_row = branch_cat_pivot.sum().to_frame().T
            total_row.index = ['Total']
            final_bc = pd.concat([branch_cat_pivot, total_row]).reset_index().rename(columns={'index': 'Branch', d_branch_col: 'Branch'})
            branch_cat_table = df_to_json_table(final_bc)

    # 4. Table 2: TOP 10 BRANDS (CR)
    brand_table = {"columns": [], "rows": []}
    if d_brand_col and d_cr_col and d_bucket_col:
        brand_filtered = df[df['Target_Bucket'].notna()]
        if not brand_filtered.empty:
            brand_pivot = brand_filtered.pivot_table(index=d_brand_col, columns='Target_Bucket', values=d_cr_col, aggfunc='sum', fill_value=0)
            brand_pivot = brand_pivot.reindex(columns=TARGET_BUCKETS, fill_value=0)
            brand_pivot['Row_Total'] = brand_pivot[TARGET_BUCKETS].sum(axis=1)
            all_brand_total = brand_pivot['Row_Total'].sum()
            brand_pivot = brand_pivot.sort_values(by='Row_Total', ascending=False).head(10)
            if all_brand_total > 0:
                brand_pivot['Share'] = ((brand_pivot['Row_Total'] / all_brand_total) * 100).round(1).astype(str) + '%'
            else:
                brand_pivot['Share'] = '0%'
            total_row = brand_pivot[TARGET_BUCKETS].sum().to_frame().T
            total_row.index = ['Total']
            top10_sum = brand_pivot['Row_Total'].sum()
            total_row['Share'] = f"{round((top10_sum / all_brand_total * 100), 1)}%" if all_brand_total > 0 else "100%"
            brand_pivot = brand_pivot.drop(columns=['Row_Total'])
            final_brand_pivot = pd.concat([brand_pivot, total_row]).reset_index().rename(columns={'index': 'Brand', d_brand_col: 'Brand'})
            final_brand_pivot.insert(0, '#', [str(i) if i < len(final_brand_pivot) else '' for i in range(1, len(final_brand_pivot)+1)])
            brand_table = df_to_json_table(final_brand_pivot)

    # 5. Table 3: AT-RISK BY BRANCH (CR)
    branch_table = {"columns": [], "rows": []}
    if d_branch_col and d_cr_col and d_bucket_col:
        filtered_branch_df = df[df[d_branch_col].astype(str).str.strip().isin(ALLOWED_BRANCHES) & df['Target_Bucket'].notna()]
        if not filtered_branch_df.empty:
            branch_pivot = filtered_branch_df.pivot_table(index=d_branch_col, columns='Target_Bucket', values=d_cr_col, aggfunc='sum', fill_value=0)
            branch_pivot = branch_pivot.reindex(columns=TARGET_BUCKETS, fill_value=0)
            branch_pivot['Row_Total'] = branch_pivot[TARGET_BUCKETS].sum(axis=1)
            grand_branch_total = branch_pivot['Row_Total'].sum()
            if grand_branch_total > 0:
                branch_pivot['Share'] = ((branch_pivot['Row_Total'] / grand_branch_total) * 100).round(1).astype(str) + '%'
            else:
                branch_pivot['Share'] = '0%'
            branch_pivot = branch_pivot.sort_values(by='Row_Total', ascending=False).drop(columns=['Row_Total'])
            total_row = branch_pivot[TARGET_BUCKETS].sum().to_frame().T
            total_row.index = ['Total']
            total_row['Share'] = '100%'
            final_branch_pivot = pd.concat([branch_pivot, total_row]).reset_index().rename(columns={'index': 'Branch', d_branch_col: 'Branch'})
            branch_table = df_to_json_table(final_branch_pivot)

    # 6. Table 7: IWO Rebalancing DC Heatmap
    heatmap_data = {"columns": [], "rows": [], "min_val": 0, "max_val": 1}
    if d_link_col and d_depot_code_col and d_cr_col:
        sku_agg_hm = df.groupby(d_link_col)[d_cr_col].sum().reset_index()
        top_10_skus = sku_agg_hm.sort_values(d_cr_col, ascending=False).head(10)[d_link_col].tolist()
        hm_sub = df[df[d_link_col].isin(top_10_skus)]
        target_depots_order = [
            'IN5H', 'IN6D', 'IN5G', 'IN5F', 'IN5C', 'IN5D',
            'IN6Z', 'IN6B', 'IN6F', 'IN6G', 'IN5V', 'IN5R',
            'IN7B', 'IN8K', 'IN7H', 'IN7D', 'IN8G', 'IN7A', 'IN8L',
            'IN7E', 'IN8Y', 'IN7T', 'IN8V', 'IN7Z', 'IN8R', 'IN7C',
            'IN34', 'IN19'
        ]
        hm_sub = hm_sub[hm_sub[d_depot_code_col].isin(target_depots_order)]
        if not hm_sub.empty:
            hm_pivot = hm_sub.pivot_table(index=d_link_col, columns=d_depot_code_col, values=d_cr_col, aggfunc='sum', fill_value=0)
            avail_depots = [c for c in target_depots_order if c in hm_pivot.columns]
            hm_pivot = hm_pivot.reindex(columns=avail_depots, fill_value=0)
            flat_hm = hm_pivot.reset_index().rename(columns={'index': 'LINK DES', d_link_col: 'LINK DES'})
            flat_hm.columns.name = None
            max_v = float(hm_pivot.max().max()) if not hm_pivot.empty else 1.0
            min_v = float(hm_pivot.min().min()) if not hm_pivot.empty else 0.0
            
            rows_json = []
            for _, r in flat_hm.iterrows():
                row_dict = {'LINK DES': str(r['LINK DES'])}
                for dep in avail_depots:
                    row_dict[dep] = round(float(r[dep]), 1)
                rows_json.append(row_dict)
            heatmap_data = {
                "columns": ['LINK DES'] + avail_depots,
                "rows": rows_json,
                "min_val": min_v,
                "max_val": max_v
            }

    return {
        "filters": {
            "week_options": week_vals,
            "branch_options": branch_vals,
            "channel_options": channel_vals
        },
        "risk_cards": {
            "high_risk_cr": round(float(high_risk_val), 1),
            "med_risk_cr": round(float(med_risk_val), 1)
        },
        "category_table": category_table,
        "branch_category_pivot": branch_cat_table,
        "brand_table": brand_table,
        "branch_table": branch_table,
        "heatmap": heatmap_data
    }

