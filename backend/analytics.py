import os
import sys
import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from parser import (
    sanitize_df, get_col_exact, sort_weeks_list, get_bucket_lower, map_to_target_bucket,
    get_channel_filter_options, TARGET_BUCKETS, ALL_BUCKETS_ORDER, ALLOWED_BRANCHES,
    STANDARD_BRANCHES, normalize_branch_filter
)
from database import get_stock_df, CACHE, load_active_or_latest_from_sqlite, get_db_connection

def calculate_sheet_data(sheet_name: str, filters: Dict[str, List[str]], limit: int = 200, offset: int = 0) -> Dict[str, Any]:
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

def calculate_dashboard_data(weeks: List[str] = [], branches: List[str] = [], channels: List[str] = []) -> Dict[str, Any]:
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
                if isinstance(val, float):
                    rec[str(col)] = round(val, 2)
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
                cat_pivot['Share'] = ((cat_pivot['Row_Total'] / grand_cat_total) * 100).round(0).astype(int).astype(str) + '%'
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
                brand_pivot['Share'] = ((brand_pivot['Row_Total'] / all_brand_total) * 100).round(0).astype(int).astype(str) + '%'
            else:
                brand_pivot['Share'] = '0%'
            total_row = brand_pivot[TARGET_BUCKETS].sum().to_frame().T
            total_row.index = ['Total']
            top10_sum = brand_pivot['Row_Total'].sum()
            total_row['Share'] = f"{int(round((top10_sum / all_brand_total * 100)))}%" if all_brand_total > 0 else "100%"
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
                branch_pivot['Share'] = ((branch_pivot['Row_Total'] / grand_branch_total) * 100).round(0).astype(int).astype(str) + '%'
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
                    row_dict[dep] = round(float(r[dep]), 2)
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
            "high_risk_cr": round(high_risk_val, 2),
            "med_risk_cr": round(med_risk_val, 2)
        },
        "category_table": category_table,
        "branch_category_pivot": branch_cat_table,
        "brand_table": brand_table,
        "branch_table": branch_table,
        "heatmap": heatmap_data
    }

def calculate_alerts_data(depots: List[str] = [], brands: List[str] = [], channels: List[str] = [], risks: List[str] = [], categories: List[str] = []) -> Dict[str, Any]:
    df = get_stock_df()
    if df is None:
        return {"error": "No stock data loaded"}

    df = df.copy()
    bucket_col = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %'])
    brand_col = get_col_exact(df, ['IOP', 'Brand', 'brand', 'BRAND'])
    depot_col = get_col_exact(df, ['Depot', 'Depot Code', 'depot', 'DEPOT'])
    material_col = get_col_exact(df, ['Material Code', 'Material code', 'MATERIAL CODE'])
    sku_desc_col = get_col_exact(df, ['SKU Des', 'SKU Description', 'link des', 'Link des'])
    cr_col = get_col_exact(df, ['Cr', 'CR', 'cr'])
    stock_col = get_col_exact(df, ['Total Stock in Case', 'Total stock in case'])
    channel_col = get_col_exact(df, ['MT', 'mt', 'Channel', 'channel'])
    
    local_matches = [c for c in df.columns if c.startswith('Local Category')]
    category_col = local_matches[1] if len(local_matches) > 1 else get_col_exact(df, ['Local Category', 'Category', 'category'])

    if cr_col: df[cr_col] = pd.to_numeric(df[cr_col], errors='coerce').fillna(0)
    if stock_col: df[stock_col] = pd.to_numeric(df[stock_col], errors='coerce').fillna(0)

    depot_vals = sorted(set(str(x) for x in df[depot_col].dropna().unique())) if depot_col else []
    brand_vals = sorted(set(str(x) for x in df[brand_col].dropna().unique())) if brand_col else []
    channel_vals = get_channel_filter_options(df, channel_col) if channel_col else []
    cat_vals = sorted(set(str(x) for x in df[category_col].dropna().unique())) if category_col else []
    risk_options = ['High (20-50%)', 'Medium (50-75%)']

    # Apply Filters
    if depot_col and depots:
        df = df[df[depot_col].astype(str).isin(depots)]
    if brand_col and brands:
        df = df[df[brand_col].astype(str).isin(brands)]
    if channel_col and channels:
        df = df[df[channel_col].astype(str).isin(channels)]
    if category_col and categories:
        df = df[df[category_col].astype(str).isin(categories)]

    bucket_risk_map = {
        '20 TO 30': 'High', '30 TO 40': 'High', '40 TO 50': 'High',
        '50 TO 60': 'Medium', '60 TO 70': 'Medium', '70 TO 75': 'Medium'
    }
    if bucket_col:
        df['Risk_Level'] = df[bucket_col].map(bucket_risk_map)
        df = df[df['Risk_Level'].notna()]
        if risks:
            allowed_risks = [r.split(' ')[0] for r in risks]
            df = df[df['Risk_Level'].isin(allowed_risks)]
    else:
        df = pd.DataFrame()

    total_high = float(df[df['Risk_Level'] == 'High'][cr_col].sum()) if (cr_col and not df.empty) else 0.0
    total_medium = float(df[df['Risk_Level'] == 'Medium'][cr_col].sum()) if (cr_col and not df.empty) else 0.0

    alerts_list = []
    if not df.empty and (sku_desc_col or material_col):
        primary_col = sku_desc_col if sku_desc_col else material_col
        agg_spec = {
            cr_col: 'sum' if cr_col else 'count',
            stock_col: 'sum' if stock_col else 'count',
            bucket_col: lambda x: ', '.join(sorted(x.dropna().unique())),
            'Risk_Level': lambda x: 'High' if 'High' in x.unique() else 'Medium'
        }
        if brand_col and brand_col != primary_col: agg_spec[brand_col] = 'first'
        if category_col and category_col != primary_col: agg_spec[category_col] = 'first'

        grouped = df.groupby(primary_col).agg(agg_spec).reset_index()
        
        def simplify_buckets(b_str):
            if pd.isna(b_str) or not b_str: return ""
            parts = str(b_str).split(', ')
            lowers, uppers = [], []
            for b in parts:
                m = re.search(r'(\d+)\s*TO\s*(\d+)', b)
                if m:
                    lowers.append(int(m.group(1)))
                    uppers.append(int(m.group(2)))
            return f"{min(lowers)}-{max(uppers)}%" if lowers and uppers else str(b_str)

        def est_days(b_str):
            if pd.isna(b_str) or not b_str: return None
            first = str(b_str).split(',')[0].strip()
            if 'TO' in first:
                try:
                    return int(int(first.split(' TO ')[0]) * 3.65)
                except:
                    return None
            return None

        def suggest_action(risk, stock):
            if risk == 'High':
                return "Initiate promotional activities or discount to accelerate movement." if stock > 100 else "Coordinate with supply chain for redistribution."
            elif risk == 'Medium':
                return "Monitor closely and consider promotional interventions if stock remains high." if stock > 200 else "Continue regular review; no immediate action required."
            return "-"

        for _, r in grouped.iterrows():
            risk_lvl = str(r['Risk_Level'])
            stk_val = float(r[stock_col]) if stock_col else 0.0
            cr_val = float(r[cr_col]) if cr_col else 0.0
            b_val = str(r[bucket_col]) if bucket_col else ""
            alerts_list.append({
                "sku_description": str(r[primary_col]),
                "brand": str(r.get(brand_col, "")),
                "shelf_life_left": simplify_buckets(b_val),
                "est_days": est_days(b_val),
                "stock_cases": int(stk_val),
                "value_cr": round(cr_val, 4),
                "risk": risk_lvl,
                "action": suggest_action(risk_lvl, stk_val)
            })
        
        alerts_list.sort(key=lambda x: x["value_cr"], reverse=True)

    high_skus = sum(1 for a in alerts_list if a['risk'] == 'High')
    med_skus = sum(1 for a in alerts_list if a['risk'] == 'Medium')

    return {
        "filters": {
            "depot_options": depot_vals,
            "brand_options": brand_vals,
            "channel_options": channel_vals,
            "category_options": cat_vals,
            "risk_options": risk_options
        },
        "kpis": {
            "high_risk_value": round(total_high, 2),
            "medium_risk_value": round(total_medium, 2),
            "high_risk_skus": high_skus,
            "medium_risk_skus": med_skus
        },
        "alerts": alerts_list
    }

def calculate_comparison_data(
    mode: str = "weekly",
    weeks: List[str] = [],
    branches: List[str] = [],
    channels: List[str] = [],
    categories: List[str] = [],
    brands: List[str] = []
) -> Dict[str, Any]:
    
    # -------------------------------------------------------------
    # MONTHLY / YEARLY COMPARISON ACROSS STORED WORKBOOKS
    # -------------------------------------------------------------
    if mode in ["monthly", "yearly"]:
        from database import preload_all_workbooks_into_ram
        if len(CACHE.get("all_workbooks", {})) == 0:
            preload_all_workbooks_into_ram()

        def get_month_display_name(filename, file_id, df_sample):
            f_lower = filename.lower()
            months = [
                ('january', 'January'), ('february', 'February'), ('march', 'March'), ('april', 'April'),
                ('may', 'May'), ('june', 'June'), ('july', 'July'), ('august', 'August'),
                ('september', 'September'), ('october', 'October'), ('november', 'November'), ('december', 'December'),
                ('jan', 'January'), ('feb', 'February'), ('mar', 'March'), ('apr', 'April'),
                ('jun', 'June'), ('jul', 'July'), ('aug', 'August'), ('sep', 'September'),
                ('oct', 'October'), ('nov', 'November'), ('dec', 'December')
            ]
            found = None
            for full_m, name_val in months:
                if full_m in f_lower:
                    found = name_val
                    break
            if not found:
                found = f"Period {file_id}"

            week_col = get_col_exact(df_sample, ['Week', 'week', 'WEEK', 'Wk'])
            if week_col:
                u_w = [str(x) for x in df_sample[week_col].dropna().unique() if str(x).strip() != '' and str(x).lower() not in ['nan', 'none']]
                if len(u_w) == 1:
                    return f"{found} ({u_w[0]})"
                elif len(u_w) > 1:
                    return f"{found} (Wk 1-{len(u_w)})"
            return found

        month_dfs = {}
        for f_id, wb_data in CACHE.get("all_workbooks", {}).items():
            f_name = wb_data["filename"]
            sheets = wb_data["sheets"]
            s_name = wb_data["stock_sheet_name"]
            df_sub = sheets.get(s_name)
            if df_sub is None:
                for s_key, s_val in sheets.items():
                    if 'master' not in s_key.lower():
                        df_sub = s_val
                        break
                if df_sub is None and sheets:
                    df_sub = list(sheets.values())[0]
            
            if df_sub is not None:
                disp_name = get_month_display_name(f_name, f_id, df_sub)
                month_dfs[disp_name] = df_sub

        all_available_periods = list(month_dfs.keys())
        if weeks and len(weeks) > 0:
            active_periods = [p for p in all_available_periods if p in weeks]
            if len(active_periods) == 0:
                active_periods = all_available_periods
        else:
            active_periods = all_available_periods

        num_periods = len(active_periods)

        # Filters on Month DataFrames
        filtered_month_dfs = {}
        for p_name in active_periods:
            m_df = month_dfs[p_name]
            c_cr_col = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if c_cr_col: m_df[c_cr_col] = pd.to_numeric(m_df[c_cr_col], errors='coerce').fillna(0)
            
            c_br_col = get_col_exact(m_df, ['Branch', 'branch', 'BRANCH'])
            c_ch_col = get_col_exact(m_df, ['MT', 'mt', 'Channel', 'channel'])
            local_matches = [c for c in m_df.columns if c.startswith('Local Category')]
            c_cat_col = local_matches[1] if len(local_matches) > 1 else get_col_exact(m_df, ['Local Category', 'Category', 'category'])
            c_brand_col = get_col_exact(m_df, ['IOP', 'Brand', 'brand', 'BRAND'])

            f_df = m_df.copy()
            if c_br_col and branches: f_df = f_df[f_df[c_br_col].astype(str).isin(normalize_branch_filter(branches))]
            if c_ch_col and channels: f_df = f_df[f_df[c_ch_col].astype(str).isin(channels)]
            if c_cat_col and categories: f_df = f_df[f_df[c_cat_col].astype(str).isin(categories)]
            if c_brand_col and brands: f_df = f_df[f_df[c_brand_col].astype(str).isin(brands)]
            filtered_month_dfs[p_name] = f_df

        # Monthly KPIs
        p_first = active_periods[0] if num_periods > 0 else None
        p_last = active_periods[-1] if num_periods > 0 else None
        
        df_first = filtered_month_dfs.get(p_first, pd.DataFrame())
        df_last = filtered_month_dfs.get(p_last, pd.DataFrame())

        cr_first = get_col_exact(df_first, ['Cr', 'CR', 'cr', 'Value'])
        cr_last = get_col_exact(df_last, ['Cr', 'CR', 'cr', 'Value'])

        val_first = float(df_first[cr_first].sum()) if (not df_first.empty and cr_first) else 0.0
        val_last = float(df_last[cr_last].sum()) if (not df_last.empty and cr_last) else 0.0

        if num_periods >= 2:
            net_change = val_last - val_first
            pct_growth = (net_change / val_first * 100) if val_first > 0 else 0.0
        else:
            net_change, pct_growth = 0.0, 0.0

        # Month Growth Driver
        cat_col_first = [c for c in df_first.columns if c.startswith('Local Category')][1] if len([c for c in df_first.columns if c.startswith('Local Category')]) > 1 else get_col_exact(df_first, ['Local Category', 'Category', 'category'])
        cat_col_last = [c for c in df_last.columns if c.startswith('Local Category')][1] if len([c for c in df_last.columns if c.startswith('Local Category')]) > 1 else get_col_exact(df_last, ['Local Category', 'Category', 'category'])

        if cat_col_first and cat_col_last and cr_first and cr_last and num_periods >= 2:
            cat_s = df_first.groupby(cat_col_first)[cr_first].sum()
            cat_e = df_last.groupby(cat_col_last)[cr_last].sum()
            diff = (cat_e - cat_s).dropna()
            driver_cat = str(diff.idxmax()) if not diff.empty else "N/A"
            driver_delta = float(diff.max()) if not diff.empty else 0.0
        else:
            driver_cat, driver_delta = "N/A", 0.0

        # Aging Index
        b_last_col = get_col_exact(df_last, ['Bucket %', 'bucket %', 'BUCKET %'])
        if b_last_col and cr_last and not df_last.empty:
            lower_map = {b: get_bucket_lower(b) for b in df_last[b_last_col].dropna().unique()}
            lowers = df_last[b_last_col].map(lower_map)
            high_risk_cr = df_last[(lowers >= 20) & (lowers < 50)][cr_last].sum()
            safe_cr = df_last[lowers >= 70][cr_last].sum()
            tot_cr = df_last[cr_last].sum()
            aging_idx_pct = (high_risk_cr / tot_cr * 100) if tot_cr > 0 else 0.0
        else:
            aging_idx_pct, safe_cr = 0.0, 0.0

        # Chart 1: Monthly Category Evolution
        cat_evolution = []
        for p_name, m_df in filtered_month_dfs.items():
            c_cat = [c for c in m_df.columns if c.startswith('Local Category')][1] if len([c for c in m_df.columns if c.startswith('Local Category')]) > 1 else get_col_exact(m_df, ['Local Category', 'Category', 'category'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if c_cat and c_cr:
                agg = m_df.groupby(c_cat)[c_cr].sum().reset_index()
                for _, r in agg.iterrows():
                    cat_evolution.append({
                        "week": p_name,
                        "category": str(r[c_cat]),
                        "value_cr": round(float(r[c_cr]), 2)
                    })

        # Chart 2: Monthly Shelf-Life Distribution Migration
        bucket_migration = []
        for p_name, m_df in filtered_month_dfs.items():
            b_col = get_col_exact(m_df, ['Bucket %', 'bucket %', 'BUCKET %'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if b_col and c_cr:
                m_df['Clean_B'] = m_df[b_col].apply(map_to_target_bucket)
                agg_b = m_df[m_df['Clean_B'].notna()].groupby('Clean_B')[c_cr].sum().reset_index()
                for _, r in agg_b.iterrows():
                    bucket_migration.append({
                        "week": p_name,
                        "bucket": str(r['Clean_B']),
                        "value_cr": round(float(r[c_cr]), 2)
                    })

        # Chart 3: Monthly Regional Branch Comparison
        branch_comparison = []
        for p_name, m_df in filtered_month_dfs.items():
            br_col = get_col_exact(m_df, ['Branch', 'branch', 'BRANCH'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if br_col and c_cr:
                agg_br = m_df[m_df[br_col].astype(str).str.strip().isin(ALLOWED_BRANCHES)].groupby(br_col)[c_cr].sum().reset_index()
                for _, r in agg_br.iterrows():
                    branch_comparison.append({
                        "branch": str(r[br_col]),
                        "week": p_name,
                        "value_cr": round(float(r[c_cr]), 2)
                    })

        # Matrix 1: Monthly Category Matrix
        cat_pivots = {}
        for p_name, m_df in filtered_month_dfs.items():
            c_cat = [c for c in m_df.columns if c.startswith('Local Category')][1] if len([c for c in m_df.columns if c.startswith('Local Category')]) > 1 else get_col_exact(m_df, ['Local Category', 'Category', 'category'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if c_cat and c_cr:
                cat_pivots[p_name] = m_df.groupby(c_cat)[c_cr].sum()

        cat_matrix_df = pd.DataFrame(cat_pivots).fillna(0)
        if num_periods >= 2:
            cat_matrix_df['Net Change (Cr)'] = cat_matrix_df[active_periods[-1]] - cat_matrix_df[active_periods[0]]
            cat_matrix_df['Growth %'] = ((cat_matrix_df['Net Change (Cr)'] / cat_matrix_df[active_periods[0]].replace(0, np.nan)) * 100).fillna(0).round(1).astype(str) + '%'

        cat_matrix_df = cat_matrix_df.sort_values(by=active_periods[-1] if active_periods else cat_matrix_df.columns[0], ascending=False)
        total_r = cat_matrix_df[active_periods].sum().to_frame().T
        total_r.index = ['Total']
        if num_periods >= 2:
            tot_net = total_r[active_periods[-1]].values[0] - total_r[active_periods[0]].values[0]
            total_r['Net Change (Cr)'] = tot_net
            total_r['Growth %'] = f"{(tot_net / total_r[active_periods[0]].values[0] * 100):.1f}%" if total_r[active_periods[0]].values[0] > 0 else "0.0%"
        
        final_cat_m = pd.concat([cat_matrix_df, total_r]).reset_index().rename(columns={'index': 'Category'})
        final_cat_m.columns.name = None
        rows_m = []
        for _, row in final_cat_m.iterrows():
            rec = {}
            for col in final_cat_m.columns:
                val = row[col]
                rec[str(col)] = round(val, 2) if isinstance(val, float) else str(val)
            rows_m.append(rec)
        cat_matrix = {"columns": [str(c) for c in final_cat_m.columns], "rows": rows_m}

        # Matrix 2: Monthly Shelf-Life Bucket Matrix
        bucket_pivots = {}
        for p_name, m_df in filtered_month_dfs.items():
            b_col = get_col_exact(m_df, ['Bucket %', 'bucket %', 'BUCKET %'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if b_col and c_cr:
                m_df['Clean_B'] = m_df[b_col].apply(map_to_target_bucket)
                bucket_pivots[p_name] = m_df[m_df['Clean_B'].notna()].groupby('Clean_B')[c_cr].sum()

        bucket_matrix_df = pd.DataFrame(bucket_pivots).fillna(0)
        avail_buckets = [b for b in ALL_BUCKETS_ORDER if b in bucket_matrix_df.index]
        bucket_matrix_df = bucket_matrix_df.reindex(avail_buckets, fill_value=0)
        if num_periods >= 2:
            bucket_matrix_df['Net Change (Cr)'] = bucket_matrix_df[active_periods[-1]] - bucket_matrix_df[active_periods[0]]
        total_b = bucket_matrix_df[active_periods].sum().to_frame().T
        total_b.index = ['Total']
        if num_periods >= 2:
            total_b['Net Change (Cr)'] = total_b[active_periods[-1]].values[0] - total_b[active_periods[0]].values[0]
        final_b_m = pd.concat([bucket_matrix_df, total_b]).reset_index().rename(columns={'index': 'Bucket %'})
        rows_bm = []
        for _, row in final_b_m.iterrows():
            rec = {}
            for col in final_b_m.columns:
                val = row[col]
                rec[str(col)] = round(val, 2) if isinstance(val, float) else str(val)
            rows_bm.append(rec)
        bucket_matrix = {"columns": [str(c) for c in final_b_m.columns], "rows": rows_bm}

        # Matrix 3: Monthly Escalating SKUs
        sku_first_col = get_col_exact(df_first, ['link des', 'link_des', 'Link des'])
        sku_last_col = get_col_exact(df_last, ['link des', 'link_des', 'Link des'])
        if sku_first_col and sku_last_col and cr_first and cr_last and num_periods >= 2:
            s_first = df_first.groupby(sku_first_col)[cr_first].sum()
            s_last = df_last.groupby(sku_last_col)[cr_last].sum()
            sku_esc = pd.DataFrame({f'{p_first} (Cr)': s_first, f'{p_last} (Cr)': s_last}).fillna(0)
            sku_esc['Net Surge (Cr)'] = sku_esc[f'{p_last} (Cr)'] - sku_esc[f'{p_first} (Cr)']
            sku_esc['Surge %'] = ((sku_esc['Net Surge (Cr)'] / sku_esc[f'{p_first} (Cr)'].replace(0, np.nan)) * 100).fillna(100).round(1).astype(str) + '%'
            sku_esc = sku_esc.sort_values(by='Net Surge (Cr)', ascending=False).head(10).reset_index().rename(columns={'index': 'SKU Description', sku_first_col: 'SKU Description'})
        else:
            s_last = df_last.groupby(sku_last_col)[cr_last].sum() if (sku_last_col and cr_last) else pd.Series()
            sku_esc = pd.DataFrame({f'{p_last} (Cr)': s_last}).fillna(0)
            sku_esc = sku_esc.sort_values(by=f'{p_last} (Cr)', ascending=False).head(10).reset_index().rename(columns={'index': 'SKU Description', sku_last_col: 'SKU Description'})

        sku_esc.insert(0, '#', [str(i) for i in range(1, len(sku_esc)+1)])
        rows_esc = []
        for _, row in sku_esc.iterrows():
            rec = {}
            for col in sku_esc.columns:
                val = row[col]
                rec[str(col)] = round(val, 2) if isinstance(val, float) else str(val)
            rows_esc.append(rec)
        escalating_skus = {"columns": [str(c) for c in sku_esc.columns], "rows": rows_esc}

        return {
            "mode": mode,
            "filters": {
                "week_options": all_available_periods,
                "active_weeks": active_periods,
                "num_weeks": num_periods,
                "branch_options": STANDARD_BRANCHES,
                "channel_options": ['TT', 'MT/ E.com / AFH'],
                "category_options": [],
                "brand_options": []
            },
            "kpis": {
                "val_end": round(val_last, 2),
                "net_4wk_change": round(net_change, 2),
                "pct_4wk_growth": round(pct_growth, 1),
                "driver_cat": str(driver_cat),
                "driver_delta": round(float(driver_delta), 2),
                "aging_idx_pct": round(aging_idx_pct, 1),
                "safe_stock_cr": round(float(safe_cr), 2)
            },
            "charts": {
                "cat_evolution": cat_evolution,
                "bucket_migration": bucket_migration,
                "branch_comparison": branch_comparison
            },
            "matrices": {
                "cat_matrix": cat_matrix,
                "bucket_matrix": bucket_matrix,
                "escalating_skus": escalating_skus
            }
        }

    # -------------------------------------------------------------
    # WEEKLY COMPARISON (WITHIN LOADED WORKBOOK)
    # -------------------------------------------------------------
    df = get_stock_df()
    if df is None:
        return {"error": "No stock data loaded"}

    df = df.copy()
    c_week_col = get_col_exact(df, ['Week', 'week', 'WEEK', 'Wk'])
    c_branch_col = get_col_exact(df, ['Branch', 'branch', 'BRANCH'])
    c_mt_col = get_col_exact(df, ['MT', 'mt', 'Channel', 'channel'])
    c_bucket_col = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %'])
    c_brand_col = get_col_exact(df, ['IOP', 'Brand', 'brand', 'BRAND'])
    
    local_matches = [c for c in df.columns if c.startswith('Local Category')]
    c_cat_col = local_matches[1] if len(local_matches) > 1 else get_col_exact(df, ['Local Category', 'Category', 'category'])
    
    c_link_col = get_col_exact(df, ['link des', 'link_des', 'Link des'])
    c_cr_col = get_col_exact(df, ['Cr', 'CR', 'cr', 'Value'])

    if c_cr_col: df[c_cr_col] = pd.to_numeric(df[c_cr_col], errors='coerce').fillna(0)

    sorted_weeks = sort_weeks_list(df[c_week_col].dropna().unique()) if c_week_col else []
    branch_vals = STANDARD_BRANCHES
    channel_vals = get_channel_filter_options(df, c_mt_col) if c_mt_col else []
    cat_vals = sorted(set(str(x) for x in df[c_cat_col].dropna().unique())) if c_cat_col else []
    brand_vals = sorted(set(str(x) for x in df[c_brand_col].dropna().unique())) if c_brand_col else []

    if weeks and len(weeks) > 0:
        active_weeks = [w for w in sorted_weeks if w in weeks]
    else:
        active_weeks = sorted_weeks[-4:] if len(sorted_weeks) >= 4 else sorted_weeks

    # Apply Filters
    filtered_comp = df.copy()
    if c_branch_col and branches:
        filtered_comp = filtered_comp[filtered_comp[c_branch_col].astype(str).isin(normalize_branch_filter(branches))]
    if c_mt_col and channels:
        filtered_comp = filtered_comp[filtered_comp[c_mt_col].astype(str).isin(channels)]
    if c_cat_col and categories:
        filtered_comp = filtered_comp[filtered_comp[c_cat_col].astype(str).isin(categories)]
    if c_brand_col and brands:
        filtered_comp = filtered_comp[filtered_comp[c_brand_col].astype(str).isin(brands)]

    num_active_weeks = len(active_weeks)
    w_start = active_weeks[0] if num_active_weeks > 0 else None
    w_end = active_weeks[-1] if num_active_weeks > 0 else None

    val_start = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_start)][c_cr_col].sum() if (w_start and c_cr_col) else 0.0
    val_end = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_end)][c_cr_col].sum() if (w_end and c_cr_col) else 0.0

    if num_active_weeks >= 2:
        net_4wk = val_end - val_start
        pct_4wk = (net_4wk / val_start * 100) if val_start > 0 else 0.0
    else:
        net_4wk = 0.0
        pct_4wk = 0.0

    # Growth driver
    if c_cat_col and c_cr_col and w_start and w_end and num_active_weeks >= 2:
        cat_s = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_start)].groupby(c_cat_col)[c_cr_col].sum()
        cat_e = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_end)].groupby(c_cat_col)[c_cr_col].sum()
        cat_diff = (cat_e - cat_s).dropna()
        driver_cat = str(cat_diff.idxmax()) if not cat_diff.empty else "N/A"
        driver_delta = float(cat_diff.max()) if not cat_diff.empty else 0.0
    elif c_cat_col and c_cr_col and w_start:
        cat_single = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_start)].groupby(c_cat_col)[c_cr_col].sum()
        driver_cat = str(cat_single.idxmax()) if not cat_single.empty else "N/A"
        driver_delta = float(cat_single.max()) if not cat_single.empty else 0.0
    else:
        driver_cat, driver_delta = "N/A", 0.0

    # Aging Index & Safe Stock
    if c_bucket_col and c_cr_col and w_end:
        end_df = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_end)]
        lower_map = {b: get_bucket_lower(b) for b in end_df[c_bucket_col].dropna().unique()}
        lowers = end_df[c_bucket_col].map(lower_map)
        high_risk_cr = end_df[(lowers >= 20) & (lowers < 50)][c_cr_col].sum()
        safe_cr = end_df[lowers >= 70][c_cr_col].sum()
        tot_cr = end_df[c_cr_col].sum()
        aging_idx_pct = (high_risk_cr / tot_cr * 100) if tot_cr > 0 else 0.0
    else:
        aging_idx_pct, safe_cr = 0.0, 0.0

    # Chart 1: Category Evolution
    cat_evolution = []
    if c_cat_col and c_week_col and c_cr_col:
        sub_c = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks)]
        cat_week_df = sub_c.groupby([c_week_col, c_cat_col])[c_cr_col].sum().reset_index()
        for _, r in cat_week_df.iterrows():
            cat_evolution.append({
                "week": str(r[c_week_col]),
                "category": str(r[c_cat_col]),
                "value_cr": round(float(r[c_cr_col]), 2)
            })

    # Chart 2: Shelf-Life Distribution Migration
    bucket_migration = []
    if c_week_col and c_bucket_col and c_cr_col:
        def is_comp_bucket(b):
            if pd.isna(b): return False
            b_clean = str(b).strip().lower().replace(' ', '')
            return b_clean in ['20to30', '30to40', '40to50', '50to60', '60to70', '70to75', '75to80', '80to85']

        sub_b = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks) & filtered_comp[c_bucket_col].apply(is_comp_bucket)]
        b_week_df = sub_b.groupby([c_week_col, c_bucket_col])[c_cr_col].sum().reset_index()
        for _, r in b_week_df.iterrows():
            bucket_migration.append({
                "week": str(r[c_week_col]),
                "bucket": str(r[c_bucket_col]),
                "value_cr": round(float(r[c_cr_col]), 2)
            })

    # Chart 3: Regional Branch Comparison
    branch_comparison = []
    if c_week_col and c_branch_col and c_cr_col:
        sub_br = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks) & filtered_comp[c_branch_col].astype(str).str.strip().isin(ALLOWED_BRANCHES)]
        br_week_df = sub_br.groupby([c_branch_col, c_week_col])[c_cr_col].sum().reset_index()
        for _, r in br_week_df.iterrows():
            branch_comparison.append({
                "branch": str(r[c_branch_col]),
                "week": str(r[c_week_col]),
                "value_cr": round(float(r[c_cr_col]), 2)
            })

    # Matrix 1: Category Matrix
    cat_matrix = {"columns": [], "rows": []}
    if c_cat_col and c_week_col and c_cr_col and num_active_weeks > 0:
        sub_c_mat = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks)]
        if not sub_c_mat.empty:
            cat_p = sub_c_mat.pivot_table(index=c_cat_col, columns=c_week_col, values=c_cr_col, aggfunc='sum', fill_value=0)
            avail_w = [w for w in active_weeks if w in cat_p.columns]
            cat_p = cat_p.reindex(columns=avail_w)
            if num_active_weeks >= 2:
                cat_p['Net Change (Cr)'] = cat_p[avail_w[-1]] - cat_p[avail_w[0]]
                cat_p['Growth %'] = ((cat_p['Net Change (Cr)'] / cat_p[avail_w[0]].replace(0, np.nan)) * 100).fillna(0).round(1).astype(str) + '%'
            
            cat_p = cat_p.sort_values(by=avail_w[-1] if avail_w else cat_p.columns[0], ascending=False)
            total_r = cat_p[avail_w].sum().to_frame().T
            total_r.index = ['Total']
            if num_active_weeks >= 2:
                net_tot = total_r[avail_w[-1]].values[0] - total_r[avail_w[0]].values[0]
                total_r['Net Change (Cr)'] = net_tot
                total_r['Growth %'] = f"{(net_tot / total_r[avail_w[0]].values[0] * 100):.1f}%" if total_r[avail_w[0]].values[0] > 0 else "0.0%"
            
            final_cat_m = pd.concat([cat_p, total_r]).reset_index().rename(columns={'index': 'Category', c_cat_col: 'Category'})
            final_cat_m.columns.name = None
            rows_m = []
            for _, row in final_cat_m.iterrows():
                rec = {}
                for col in final_cat_m.columns:
                    val = row[col]
                    rec[str(col)] = round(val, 2) if isinstance(val, float) else str(val)
                rows_m.append(rec)
            cat_matrix = {"columns": [str(c) for c in final_cat_m.columns], "rows": rows_m}

    # Matrix 2: Shelf-Life Bucket Matrix
    bucket_matrix = {"columns": [], "rows": []}
    if c_bucket_col and c_week_col and c_cr_col and num_active_weeks > 0:
        sub_b_mat = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks)]
        if not sub_b_mat.empty:
            b_p = sub_b_mat.pivot_table(index=c_bucket_col, columns=c_week_col, values=c_cr_col, aggfunc='sum', fill_value=0)
            avail_w = [w for w in active_weeks if w in b_p.columns]
            b_p = b_p.reindex(columns=avail_w)
            if num_active_weeks >= 2:
                b_p['Net Change (Cr)'] = b_p[avail_w[-1]] - b_p[avail_w[0]]
            b_p['SortKey'] = [get_bucket_lower(b) or 999 for b in b_p.index]
            b_p = b_p.sort_values('SortKey').drop('SortKey', axis=1)
            total_b = b_p[avail_w].sum().to_frame().T
            total_b.index = ['Total']
            if num_active_weeks >= 2:
                total_b['Net Change (Cr)'] = total_b[avail_w[-1]].values[0] - total_b[avail_w[0]].values[0]
            final_b_m = pd.concat([b_p, total_b]).reset_index().rename(columns={'index': 'Bucket %', c_bucket_col: 'Bucket %'})
            final_b_m.columns.name = None
            rows_bm = []
            for _, row in final_b_m.iterrows():
                rec = {}
                for col in final_b_m.columns:
                    val = row[col]
                    rec[str(col)] = round(val, 2) if isinstance(val, float) else str(val)
                rows_bm.append(rec)
            bucket_matrix = {"columns": [str(c) for c in final_b_m.columns], "rows": rows_bm}

    # Matrix 3: Top Escalating SKUs
    escalating_skus = {"columns": [], "rows": []}
    if c_link_col and c_week_col and c_cr_col and num_active_weeks > 0:
        if num_active_weeks >= 2:
            s_first = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_start)].groupby(c_link_col)[c_cr_col].sum()
            s_last = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_end)].groupby(c_link_col)[c_cr_col].sum()
            sku_esc = pd.DataFrame({f'{w_start} (Cr)': s_first, f'{w_end} (Cr)': s_last}).fillna(0)
            sku_esc['Net Surge (Cr)'] = sku_esc[f'{w_end} (Cr)'] - sku_esc[f'{w_start} (Cr)']
            sku_esc['Surge %'] = ((sku_esc['Net Surge (Cr)'] / sku_esc[f'{w_start} (Cr)'].replace(0, np.nan)) * 100).fillna(100).round(1).astype(str) + '%'
            sku_esc = sku_esc.sort_values(by='Net Surge (Cr)', ascending=False).head(10).reset_index().rename(columns={'index': 'SKU Description', c_link_col: 'SKU Description'})
        else:
            s_single = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_start)].groupby(c_link_col)[c_cr_col].sum()
            sku_esc = pd.DataFrame({f'{w_start} (Cr)': s_single}).fillna(0)
            sku_esc = sku_esc.sort_values(by=f'{w_start} (Cr)', ascending=False).head(10).reset_index().rename(columns={'index': 'SKU Description', c_link_col: 'SKU Description'})

        sku_esc.insert(0, '#', [str(i) for i in range(1, len(sku_esc)+1)])
        rows_esc = []
        for _, row in sku_esc.iterrows():
            rec = {}
            for col in sku_esc.columns:
                val = row[col]
                rec[str(col)] = round(val, 2) if isinstance(val, float) else str(val)
            rows_esc.append(rec)
        escalating_skus = {"columns": [str(c) for c in sku_esc.columns], "rows": rows_esc}

    return {
        "mode": "weekly",
        "filters": {
            "week_options": sorted_weeks,
            "active_weeks": active_weeks,
            "num_weeks": num_active_weeks,
            "branch_options": branch_vals,
            "channel_options": channel_vals,
            "category_options": cat_vals,
            "brand_options": brand_vals
        },
        "kpis": {
            "val_end": round(val_end, 2),
            "net_4wk_change": round(net_4wk, 2),
            "pct_4wk_growth": round(pct_4wk, 1),
            "driver_cat": str(driver_cat),
            "driver_delta": round(float(driver_delta), 2),
            "aging_idx_pct": round(aging_idx_pct, 1),
            "safe_stock_cr": round(float(safe_cr), 2)
        },
        "charts": {
            "cat_evolution": cat_evolution,
            "bucket_migration": bucket_migration,
            "branch_comparison": branch_comparison
        },
        "matrices": {
            "cat_matrix": cat_matrix,
            "bucket_matrix": bucket_matrix,
            "escalating_skus": escalating_skus
        }
    }

def calculate_trend_data(dimension: str = "Category", metric: str = "At-Risk Value (Cr)", top_n: Union[int, str] = 10, branches: List[str] = []) -> Dict[str, Any]:
    df = get_stock_df()
    if df is None:
        return {"error": "No stock data loaded"}

    df = df.copy()
    t_week_col = get_col_exact(df, ['Week', 'week', 'WEEK', 'Wk'])
    t_branch_col = get_col_exact(df, ['Branch', 'branch', 'BRANCH'])
    t_mt_col = get_col_exact(df, ['MT', 'mt', 'Channel', 'channel'])
    t_bucket_col = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %'])
    t_brand_col = get_col_exact(df, ['IOP', 'Brand', 'brand', 'BRAND'])
    
    local_matches = [c for c in df.columns if c.startswith('Local Category')]
    t_cat_col = local_matches[1] if len(local_matches) > 1 else get_col_exact(df, ['Local Category', 'Category', 'category'])
    
    t_link_col = get_col_exact(df, ['link des', 'link_des', 'Link des'])
    t_cr_col = get_col_exact(df, ['Cr', 'CR', 'cr', 'Value'])
    t_stock_col = get_col_exact(df, ['Total Stock in Case', 'Total stock in case', 'Stock'])

    if t_cr_col: df[t_cr_col] = pd.to_numeric(df[t_cr_col], errors='coerce').fillna(0)
    if t_stock_col: df[t_stock_col] = pd.to_numeric(df[t_stock_col], errors='coerce').fillna(0)

    if t_bucket_col:
        bucket_lower_map = {b: get_bucket_lower(b) for b in df[t_bucket_col].dropna().unique()}
        df['Bucket_Lower'] = df[t_bucket_col].map(bucket_lower_map)
        df['Is_High_Risk'] = df['Bucket_Lower'].apply(lambda x: 1 if pd.notna(x) and 20 <= x < 50 else 0)
        df['Is_Safe_Stock'] = df['Bucket_Lower'].apply(lambda x: 1 if pd.notna(x) and x >= 70 else 0)
        df['Clean_Bucket'] = df[t_bucket_col].apply(map_to_target_bucket)
    else:
        df['Is_High_Risk'] = 0
        df['Is_Safe_Stock'] = 1
        df['Clean_Bucket'] = None

    df['High_Risk_Cr'] = np.where(df['Is_High_Risk'] == 1, df[t_cr_col], 0.0) if t_cr_col else 0.0

    dim_options = {}
    if t_cat_col: dim_options["Category"] = t_cat_col
    if t_brand_col: dim_options["Brand (IOP)"] = t_brand_col
    if t_link_col: dim_options["Product / SKU"] = t_link_col
    if t_branch_col: dim_options["Branch"] = t_branch_col

    chosen_dim_col = dim_options.get(dimension, t_cat_col)
    branch_vals = STANDARD_BRANCHES

    filtered_tr = df.copy()
    if t_branch_col and branches:
        filtered_tr = filtered_tr[filtered_tr[t_branch_col].astype(str).isin(normalize_branch_filter(branches))]

    total_val_all = float(filtered_tr[t_cr_col].sum()) if t_cr_col else 0.0

    # Trend KPIs
    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
        dim_totals = filtered_tr.groupby(chosen_dim_col)[t_cr_col].sum().sort_values(ascending=False)
        top_contributor = str(dim_totals.index[0]) if not dim_totals.empty else "N/A"
        top_val = float(dim_totals.iloc[0]) if not dim_totals.empty else 0.0
        top_pct = (top_val / total_val_all * 100) if total_val_all > 0 else 0.0
        cum_share = dim_totals.cumsum() / total_val_all
        pareto_count = int(len(cum_share[cum_share <= 0.80]) + 1)
        pareto_pct = (pareto_count / len(dim_totals) * 100) if len(dim_totals) > 0 else 0.0
    else:
        top_contributor, top_val, top_pct, pareto_count, pareto_pct = "N/A", 0.0, 0.0, 0, 0.0

    safe_val = float(filtered_tr[filtered_tr['Is_Safe_Stock'] == 1][t_cr_col].sum()) if t_cr_col else 0.0
    freshness_ratio = (safe_val / total_val_all * 100) if total_val_all > 0 else 100.0
    high_risk_val = float(filtered_tr[filtered_tr['Is_High_Risk'] == 1][t_cr_col].sum()) if t_cr_col else 0.0
    high_risk_pct = (high_risk_val / total_val_all * 100) if total_val_all > 0 else 0.0

    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
        item_ranks = filtered_tr.groupby(chosen_dim_col)[t_cr_col].sum().sort_values(ascending=False)
        target_items = item_ranks.head(int(top_n)).index.tolist() if top_n != "All" else item_ranks.index.tolist()
        plot_df = filtered_tr[filtered_tr[chosen_dim_col].isin(target_items)]
    else:
        target_items = []
        plot_df = filtered_tr.copy()

    # 1. Trajectory Time-series
    trajectory_data = []
    if t_week_col and chosen_dim_col and not plot_df.empty:
        if metric == "At-Risk Value (Cr)":
            t_agg = plot_df.groupby([t_week_col, chosen_dim_col])[t_cr_col].sum().reset_index()
            y_col = t_cr_col
        elif metric == "Total Stock (Cases)":
            t_agg = plot_df.groupby([t_week_col, chosen_dim_col])[t_stock_col].sum().reset_index()
            y_col = t_stock_col
        else:
            t_agg = plot_df.groupby([t_week_col, chosen_dim_col]).apply(
                lambda g: (g[g['Is_High_Risk'] == 1][t_cr_col].sum() / g[t_cr_col].sum() * 100) if g[t_cr_col].sum() > 0 else 0
            ).reset_index(name='High_Risk_Pct')
            y_col = 'High_Risk_Pct'

        for _, r in t_agg.iterrows():
            trajectory_data.append({
                "week": str(r[t_week_col]),
                "item": str(r[chosen_dim_col]),
                "value": round(float(r[y_col]), 2)
            })

    # 2. Pareto Exposure Data
    pareto_data = []
    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
        pareto_df = filtered_tr.groupby(chosen_dim_col)[t_cr_col].sum().sort_values(ascending=False).reset_index()
        pareto_df = pareto_df.head(int(top_n)) if top_n != "All" else pareto_df.head(15)
        tot_p = pareto_df[t_cr_col].sum()
        pareto_df['Cum_Val'] = pareto_df[t_cr_col].cumsum()
        pareto_df['Cum_Pct'] = ((pareto_df['Cum_Val'] / tot_p) * 100).round(1) if tot_p > 0 else 0
        for _, r in pareto_df.iterrows():
            pareto_data.append({
                "item": str(r[chosen_dim_col]),
                "value_cr": round(float(r[t_cr_col]), 2),
                "cum_pct": round(float(r['Cum_Pct']), 1)
            })

    # 3. Health Profile (Strictly ordered: 20 TO 30 to 80 to 85)
    comp_data = []
    if chosen_dim_col and t_bucket_col and t_cr_col and target_items:
        comp_df = filtered_tr[
            filtered_tr[chosen_dim_col].isin(target_items[:8]) & 
            filtered_tr['Clean_Bucket'].isin(ALL_BUCKETS_ORDER)
        ]
        if not comp_df.empty:
            comp_pivot = comp_df.pivot_table(index=chosen_dim_col, columns='Clean_Bucket', values=t_cr_col, aggfunc='sum', fill_value=0)
            avail_buckets = [b for b in ALL_BUCKETS_ORDER if b in comp_pivot.columns]
            comp_pivot = comp_pivot.reindex(columns=avail_buckets, fill_value=0)
            for item, row in comp_pivot.iterrows():
                for b in avail_buckets:
                    comp_data.append({
                        "item": str(item),
                        "bucket": b,
                        "value_cr": round(float(row[b]), 2)
                    })

    # 4. Regional Branch Breakdown for Top Items (01.North, 02.East, 03.West, 04.South)
    branch_breakdown_data = []
    if chosen_dim_col and t_branch_col and t_cr_col and target_items:
        br_df = filtered_tr[
            filtered_tr[chosen_dim_col].isin(target_items[:8]) & 
            filtered_tr[t_branch_col].astype(str).isin(['01.North', '02.East', '03.West', '04.South', '1.North', '2.East', '3.West', '4.South', 'North', 'East', 'West', 'South'])
        ]
        if not br_df.empty:
            br_pivot = br_df.pivot_table(index=chosen_dim_col, columns=t_branch_col, values=t_cr_col, aggfunc='sum', fill_value=0)
            for item, row in br_pivot.iterrows():
                for br in br_pivot.columns:
                    branch_breakdown_data.append({
                        "item": str(item),
                        "branch": str(br),
                        "value_cr": round(float(row[br]), 2)
                    })

    # 5. Leaderboard Table
    leaderboard = []
    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
        agg_spec = {t_cr_col: 'sum', 'High_Risk_Cr': 'sum'}
        if t_stock_col: agg_spec[t_stock_col] = 'sum'
        lb_df = filtered_tr.groupby(chosen_dim_col).agg(agg_spec).reset_index()
        
        for idx, r in lb_df.sort_values(by=t_cr_col, ascending=False).reset_index(drop=True).iterrows():
            val = float(r[t_cr_col])
            hr_val = float(r['High_Risk_Cr'])
            stk_c = float(r[t_stock_col]) if t_stock_col else 0.0
            hr_pct = (hr_val / val * 100) if val > 0 else 0.0
            share_tot = (val / total_val_all * 100) if total_val_all > 0 else 0.0

            if hr_pct >= 40 and val > 1.0:
                strat = "Urgent Flash Liquidation / BOGO"
            elif hr_pct >= 40:
                strat = "Targeted Channel Promotion"
            elif val > 1.0:
                strat = "Priority Fast-Track Distribution"
            else:
                strat = "Regular Supply Chain Monitoring"

            leaderboard.append({
                "rank": f"#{idx+1}",
                "item": str(r[chosen_dim_col]),
                "total_exposure_cr": round(val, 2),
                "high_risk_cr": round(hr_val, 2),
                "stock_cases": int(stk_c),
                "high_risk_pct": f"{hr_pct:.1f}%",
                "share_pct": f"{share_tot:.1f}%",
                "prescribed_strategy": strat
            })

    return {
        "filters": {
            "dim_options": list(dim_options.keys()),
            "metric_options": ["At-Risk Value (Cr)", "Total Stock (Cases)", "% Critical Risk (<50% life)"],
            "top_n_options": [5, 10, 15, "All"],
            "branch_options": branch_vals
        },
        "kpis": {
            "top_contributor_val": round(top_val, 2),
            "top_contributor_name": str(top_contributor),
            "top_contributor_pct": round(top_pct, 1),
            "pareto_count": pareto_count,
            "pareto_pct": round(pareto_pct, 0),
            "high_risk_pct": round(high_risk_pct, 1),
            "high_risk_val": round(high_risk_val, 2),
            "freshness_ratio": round(freshness_ratio, 1)
        },
        "charts": {
            "trajectory": trajectory_data,
            "pareto": pareto_data,
            "composition": comp_data,
            "shelf_life_comp": comp_data,
            "branch_breakdown": branch_breakdown_data
        },
        "leaderboard": leaderboard
    }
