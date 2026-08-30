import os
import sys
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from parser import (
    get_col_exact, sort_weeks_list, get_bucket_lower, map_to_target_bucket,
    get_channel_filter_options, ALLOWED_BRANCHES, STANDARD_BRANCHES,
    normalize_branch_filter
)
from database import get_stock_df, CACHE

# User-customized comparison bucket order (only up to 70 TO 75)
COMPARISON_BUCKETS_ORDER = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75']

def calculate_comparison_data(
    mode: str = "weekly",
    weeks: List[str] = [],
    branches: List[str] = [],
    channels: List[str] = [],
    categories: List[str] = [],
    brands: List[str] = []
) -> Dict[str, Any]:
    """
    Handles Multi-period comparisons:
    - mode = 'weekly': within active 4-week file (WoW delta & category/bucket matrices)
    - mode = 'monthly': across uploaded monthly workbooks (MoM delta & monthly matrices)
    - mode = 'yearly': across annual datasets (YoY delta & annual matrices)
    """
    
    # -------------------------------------------------------------
    # MONTHLY / YEARLY COMPARISON ACROSS STORED WORKBOOKS
    # -------------------------------------------------------------
    if mode in ["monthly", "yearly"]:
        from database import preload_all_workbooks_into_ram
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

        # Multi-Period Executive Overview KPI Cards
        executive_cards = []
        prev_high = None
        period_type = "Month" if mode == "monthly" else "Year"
        for idx, p_name in enumerate(active_periods):
            m_df = filtered_month_dfs.get(p_name, pd.DataFrame())
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            c_b = get_col_exact(m_df, ['Bucket %', 'bucket %', 'BUCKET %'])
            if c_b and c_cr and not m_df.empty:
                lower_map = {b: get_bucket_lower(b) for b in m_df[c_b].dropna().unique()}
                lowers = m_df[c_b].map(lower_map)
                high_cr = float(m_df[(lowers >= 20) & (lowers < 50)][c_cr].sum())
            else:
                high_cr = float(m_df[c_cr].sum()) if c_cr and not m_df.empty else 0.0

            if idx > 0 and prev_high is not None:
                delta_high = high_cr - prev_high
                delta_pct = (delta_high / prev_high * 100) if prev_high > 0 else 0.0
                suffix = "MoM" if mode == "monthly" else "YoY"
                delta_str = f"{delta_high:+.2f} Cr ({delta_pct:+.1f}% {suffix})"
            else:
                delta_high = 0.0
                delta_pct = 0.0
                delta_str = f"Baseline {period_type}"

            prev_high = high_cr
            executive_cards.append({
                "period": str(p_name),
                "label": str(p_name),
                "title": f"{p_name} High Risk",
                "value_cr": round(high_cr, 2),
                "delta_str": delta_str,
                "delta_cr": round(delta_high, 2),
                "delta_pct": round(delta_pct, 1),
                "is_baseline": idx == 0
            })

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
                filtered_buckets = m_df[m_df['Clean_B'].isin(COMPARISON_BUCKETS_ORDER)]
                agg_b = filtered_buckets.groupby('Clean_B')[c_cr].sum().reset_index()
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
            if c_cat and c_cr and not m_df.empty:
                cat_pivots[p_name] = m_df.groupby(c_cat)[c_cr].sum()

        cat_matrix_df = pd.DataFrame(cat_pivots).fillna(0)
        cat_matrix = {"columns": [], "rows": []}
        if not cat_matrix_df.empty and active_periods:
            avail_cols = [p for p in active_periods if p in cat_matrix_df.columns]
            if len(avail_cols) >= 2:
                cat_matrix_df['Net Change (Cr)'] = cat_matrix_df[avail_cols[-1]] - cat_matrix_df[avail_cols[0]]
                cat_matrix_df['Growth %'] = ((cat_matrix_df['Net Change (Cr)'] / cat_matrix_df[avail_cols[0]].replace(0, np.nan)) * 100).fillna(0).round(1).astype(str) + '%'

            cat_matrix_df = cat_matrix_df.sort_values(by=avail_cols[-1] if avail_cols else cat_matrix_df.columns[0], ascending=False)
            total_r = cat_matrix_df[avail_cols].sum().to_frame().T
            total_r.index = ['Total']
            if len(avail_cols) >= 2 and not total_r.empty:
                val_e = float(total_r[avail_cols[-1]].values[0]) if len(total_r[avail_cols[-1]].values) > 0 else 0.0
                val_s = float(total_r[avail_cols[0]].values[0]) if len(total_r[avail_cols[0]].values) > 0 else 0.0
                tot_net = val_e - val_s
                total_r['Net Change (Cr)'] = tot_net
                total_r['Growth %'] = f"{(tot_net / val_s * 100):.1f}%" if val_s > 0 else "0.0%"
            
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

        # Matrix 2: Monthly Shelf-Life Bucket Matrix (only up to 70 TO 75)
        bucket_pivots = {}
        for p_name, m_df in filtered_month_dfs.items():
            b_col = get_col_exact(m_df, ['Bucket %', 'bucket %', 'BUCKET %'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if b_col and c_cr and not m_df.empty:
                m_df['Clean_B'] = m_df[b_col].apply(map_to_target_bucket)
                filtered_df_buckets = m_df[m_df['Clean_B'].isin(COMPARISON_BUCKETS_ORDER)]
                bucket_pivots[p_name] = filtered_df_buckets.groupby('Clean_B')[c_cr].sum()

        bucket_matrix_df = pd.DataFrame(bucket_pivots).fillna(0)
        bucket_matrix = {"columns": [], "rows": []}
        if not bucket_matrix_df.empty and active_periods:
            avail_buckets = [b for b in COMPARISON_BUCKETS_ORDER if b in bucket_matrix_df.index]
            bucket_matrix_df = bucket_matrix_df.reindex(avail_buckets, fill_value=0)
            avail_p = [p for p in active_periods if p in bucket_matrix_df.columns]
            if len(avail_p) >= 2:
                bucket_matrix_df['Net Change (Cr)'] = bucket_matrix_df[avail_p[-1]] - bucket_matrix_df[avail_p[0]]
            total_b = bucket_matrix_df[avail_p].sum().to_frame().T
            total_b.index = ['Total']
            if len(avail_p) >= 2 and not total_b.empty:
                val_e = float(total_b[avail_p[-1]].values[0]) if len(total_b[avail_p[-1]].values) > 0 else 0.0
                val_s = float(total_b[avail_p[0]].values[0]) if len(total_b[avail_p[0]].values) > 0 else 0.0
                total_b['Net Change (Cr)'] = val_e - val_s
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
        elif df_last is not None and not df_last.empty and sku_last_col and cr_last:
            s_last = df_last.groupby(sku_last_col)[cr_last].sum()
            sku_esc = pd.DataFrame({f'{p_last} (Cr)': s_last}).fillna(0)
            sku_esc = sku_esc.sort_values(by=f'{p_last} (Cr)', ascending=False).head(10).reset_index().rename(columns={'index': 'SKU Description', sku_last_col: 'SKU Description'})
        else:
            sku_esc = pd.DataFrame(columns=['#', 'SKU Description', 'Value (Cr)'])

        if not sku_esc.empty and '#' not in sku_esc.columns:
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
                "executive_cards": executive_cards,
                "overview_title": f"{len(executive_cards)}-{period_type} Executive Overview",
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

    # 4-Week Executive Overview KPI Cards (High Risk Value & WoW Delta)
    executive_cards = []
    prev_high = None
    for idx, wk in enumerate(active_weeks):
        wk_df = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(wk)]
        if c_bucket_col and c_cr_col and not wk_df.empty:
            lower_map = {b: get_bucket_lower(b) for b in wk_df[c_bucket_col].dropna().unique()}
            lowers = wk_df[c_bucket_col].map(lower_map)
            high_cr = float(wk_df[(lowers >= 20) & (lowers < 50)][c_cr_col].sum())
        else:
            high_cr = float(wk_df[c_cr_col].sum()) if c_cr_col and not wk_df.empty else 0.0

        if idx > 0 and prev_high is not None:
            delta_high = high_cr - prev_high
            delta_pct = (delta_high / prev_high * 100) if prev_high > 0 else 0.0
            delta_str = f"{delta_high:+.2f} Cr ({delta_pct:+.1f}% WoW)"
        else:
            delta_high = 0.0
            delta_pct = 0.0
            delta_str = "Baseline Week"

        prev_high = high_cr
        wk_display = str(wk) if str(wk).lower().startswith('week') else f"Week {wk}"
        executive_cards.append({
            "period": str(wk),
            "label": wk_display,
            "title": f"{wk_display} High Risk",
            "value_cr": round(high_cr, 2),
            "delta_str": delta_str,
            "delta_cr": round(delta_high, 2),
            "delta_pct": round(delta_pct, 1),
            "is_baseline": idx == 0
        })

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

    # Chart 2: Shelf-Life Distribution Migration (only up to 70 TO 75)
    bucket_migration = []
    if c_week_col and c_bucket_col and c_cr_col:
        def is_comp_bucket(b):
            if pd.isna(b): return False
            b_clean = str(b).strip().lower().replace(' ', '')
            return b_clean in ['20to30', '30to40', '40to50', '50to60', '60to70', '70to75']

        sub_b = filtered_comp[
            filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks) & 
            filtered_comp[c_bucket_col].apply(is_comp_bucket)
        ]
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
            if len(avail_w) >= 2:
                cat_p['Net Change (Cr)'] = cat_p[avail_w[-1]] - cat_p[avail_w[0]]
                cat_p['Growth %'] = ((cat_p['Net Change (Cr)'] / cat_p[avail_w[0]].replace(0, np.nan)) * 100).fillna(0).round(1).astype(str) + '%'
            
            cat_p = cat_p.sort_values(by=avail_w[-1] if avail_w else cat_p.columns[0], ascending=False)
            total_r = cat_p[avail_w].sum().to_frame().T
            total_r.index = ['Total']
            if len(avail_w) >= 2 and not total_r.empty:
                val_e = float(total_r[avail_w[-1]].values[0]) if len(total_r[avail_w[-1]].values) > 0 else 0.0
                val_s = float(total_r[avail_w[0]].values[0]) if len(total_r[avail_w[0]].values) > 0 else 0.0
                net_tot = val_e - val_s
                total_r['Net Change (Cr)'] = net_tot
                total_r['Growth %'] = f"{(net_tot / val_s * 100):.1f}%" if val_s > 0 else "0.0%"
            
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

    # Matrix 2: Shelf-Life Bucket Matrix (only up to 70 TO 75)
    bucket_matrix = {"columns": [], "rows": []}
    if c_bucket_col and c_week_col and c_cr_col and num_active_weeks > 0:
        sub_b_mat = filtered_comp[
            filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks) &
            filtered_comp[c_bucket_col].astype(str).isin(COMPARISON_BUCKETS_ORDER)
        ]
        if not sub_b_mat.empty:
            b_p = sub_b_mat.pivot_table(index=c_bucket_col, columns=c_week_col, values=c_cr_col, aggfunc='sum', fill_value=0)
            avail_w = [w for w in active_weeks if w in b_p.columns]
            b_p = b_p.reindex(columns=avail_w)
            if len(avail_w) >= 2:
                b_p['Net Change (Cr)'] = b_p[avail_w[-1]] - b_p[avail_w[0]]
            b_p['SortKey'] = [get_bucket_lower(b) or 999 for b in b_p.index]
            b_p = b_p.sort_values('SortKey').drop('SortKey', axis=1)
            total_b = b_p[avail_w].sum().to_frame().T
            total_b.index = ['Total']
            if len(avail_w) >= 2 and not total_b.empty:
                val_e = float(total_b[avail_w[-1]].values[0]) if len(total_b[avail_w[-1]].values) > 0 else 0.0
                val_s = float(total_b[avail_w[0]].values[0]) if len(total_b[avail_w[0]].values) > 0 else 0.0
                total_b['Net Change (Cr)'] = val_e - val_s
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
            "executive_cards": executive_cards,
            "overview_title": f"{len(executive_cards)}-Week Executive Overview",
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

