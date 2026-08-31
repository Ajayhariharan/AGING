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

SKU_BUCKET_COLS = ['<30%', '30-40%', '40-50%', '50-60%', '60-70%', '70-75%', '75-80%']

def map_sku_matrix_bucket(b):
    if pd.isna(b): return None
    b_str = str(b).strip().upper()
    if '20 TO 30' in b_str or '<30' in b_str or '20-30' in b_str or '20TO30' in b_str or '< 30' in b_str:
        return '<30%'
    if '30 TO 40' in b_str or '30-40' in b_str or '30TO40' in b_str:
        return '30-40%'
    if '40 TO 50' in b_str or '40-50' in b_str or '40TO50' in b_str:
        return '40-50%'
    if '50 TO 60' in b_str or '50-60' in b_str or '50TO60' in b_str:
        return '50-60%'
    if '60 TO 70' in b_str or '60-70' in b_str or '60TO70' in b_str:
        return '60-70%'
    if '70 TO 75' in b_str or '70-75' in b_str or '70TO75' in b_str:
        return '70-75%'
    if '75 TO 80' in b_str or '75-80' in b_str or '75TO80' in b_str or '80 TO 85' in b_str or '80-85' in b_str or '>75' in b_str or '> 75' in b_str or '75-80%' in b_str:
        return '75-80%'
    return None

def build_sku_shelf_life_matrix(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"columns": ["Brand", "Link Description"] + SKU_BUCKET_COLS + ["Total"], "rows": []}
    
    c_brand = get_col_exact(df, ['Brand', 'brand', 'BRAND', 'IOP', 'iop', 'IOP Cat', 'Iop Category'])
    c_link = get_col_exact(df, ['link des', 'Link des', 'LINK DES', 'SKU Des', 'SKU Description', 'Material Description', 'Description', 'Link Description', 'Base code Des.'])
    c_bucket = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %', 'Shelf life left %', 'Shelf Life Bucket', 'Bucket'])
    c_cr = get_col_exact(df, ['Cr', 'CR', 'cr', 'Value', 'Stock in tons', 'Stock Value (Cr)', 'Stock'])

    if not c_bucket or not c_cr:
        return {"columns": ["Brand", "Link Description"] + SKU_BUCKET_COLS + ["Total"], "rows": []}
    
    df_work = df.copy()
    if not c_brand:
        df_work['Brand_Temp'] = 'All Brands'
        c_brand = 'Brand_Temp'
    if not c_link:
        df_work['Link_Temp'] = df_work[c_brand]
        c_link = 'Link_Temp'
        
    df_work['Clean_SKU_Bucket'] = df_work[c_bucket].apply(map_sku_matrix_bucket)
    df_work = df_work[df_work['Clean_SKU_Bucket'].notna()]
    if df_work.empty:
        return {"columns": ["Brand", "Link Description"] + SKU_BUCKET_COLS + ["Total"], "rows": []}

    df_work[c_cr] = pd.to_numeric(df_work[c_cr], errors='coerce').fillna(0)
    sku_pivot = df_work.pivot_table(index=[c_brand, c_link], columns='Clean_SKU_Bucket', values=c_cr, aggfunc='sum', fill_value=0)
    sku_pivot = sku_pivot.reindex(columns=SKU_BUCKET_COLS, fill_value=0)
    sku_pivot['Total'] = sku_pivot[SKU_BUCKET_COLS].sum(axis=1)
    
    sku_pivot = sku_pivot[sku_pivot['Total'] > 0]
    sku_pivot = sku_pivot.sort_values(by='Total', ascending=False).head(35)
    
    total_r = sku_pivot[SKU_BUCKET_COLS + ['Total']].sum().to_frame().T
    total_r.index = pd.MultiIndex.from_tuples([('Total', '')], names=[c_brand, c_link])
    
    final_sku_df = pd.concat([sku_pivot, total_r]).reset_index()
    final_sku_df = final_sku_df.rename(columns={c_brand: 'Brand', c_link: 'Link Description'})
    
    rows_sku = []
    for _, r in final_sku_df.iterrows():
        rec = {}
        for col in final_sku_df.columns:
            val = r[col]
            rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
        rows_sku.append(rec)
    
    return {
        "columns": ["Brand", "Link Description"] + SKU_BUCKET_COLS + ["Total"],
        "rows": rows_sku
    }

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

            return found

        month_order_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }

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

        raw_periods = list(month_dfs.keys())
        # Sort chronologically by calendar month if matching
        all_available_periods = sorted(raw_periods, key=lambda x: month_order_map.get(x.lower(), 99))
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
                delta_str = f"{delta_high:+.1f} Cr ({delta_pct:+.1f}% {suffix})"
            else:
                delta_high = 0.0
                delta_pct = 0.0
                delta_str = f"Baseline {period_type}"

            prev_high = high_cr
            executive_cards.append({
                "period": str(p_name),
                "label": str(p_name),
                "title": f"{p_name} High Risk",
                "value_cr": round(float(high_cr), 1),
                "delta_str": delta_str,
                "delta_cr": round(float(delta_high), 1),
                "delta_pct": round(delta_pct, 1),
                "is_baseline": idx == 0
            })

        # Check if 12 months exist for yearly comparison
        is_complete_year = len(all_available_periods) >= 12
        if mode == "yearly" and not is_complete_year:
            return {
                "mode": "yearly",
                "is_complete_year": False,
                "available_months_count": len(all_available_periods),
                "available_months": all_available_periods,
                "missing_months_count": max(0, 12 - len(all_available_periods)),
                "message": f"Please add respective 12 months data to enable Yearly Comparison (currently only {len(all_available_periods)}/12 months loaded).",
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
                    "overview_title": "Yearly Comparison (12 Months Required)",
                    "val_end": round(float(val_last), 1),
                    "net_4wk_change": round(float(net_change), 1),
                    "pct_4wk_growth": round(pct_growth, 1),
                    "driver_cat": str(driver_cat),
                    "driver_delta": round(float(driver_delta), 1),
                    "aging_idx_pct": round(aging_idx_pct, 1),
                    "safe_stock_cr": round(float(safe_cr), 1)
                },
                "charts": {
                    "red_zone_trajectory": [],
                    "cat_baseline_vs_current": [],
                    "liquidation_velocity": [],
                    "cat_evolution": [],
                    "bucket_migration": [],
                    "branch_comparison": []
                },
                "matrices": {
                    "cat_matrix": {"columns": [], "rows": []},
                    "bucket_matrix": {"columns": [], "rows": []},
                    "brand_surplus_matrix": {"columns": [], "rows": []},
                    "escalating_skus": {"columns": [], "rows": []}
                }
            }

        # Chart 1: 100% Stacked Bar Chart – Shelf-Life Composition Shift (Red-Zone vs Safe Stock)
        shelf_life_composition_shift = []
        for p_name, m_df in filtered_month_dfs.items():
            b_col = get_col_exact(m_df, ['Bucket %', 'bucket %', 'BUCKET %'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if b_col and c_cr and not m_df.empty:
                m_df['Clean_B'] = m_df[b_col].apply(map_to_target_bucket)
                danger_cr = float(m_df[m_df['Clean_B'].isin(['20 TO 30', '30 TO 40', '40 TO 50'])][c_cr].sum())
                safe_cr = float(m_df[~m_df['Clean_B'].isin(['20 TO 30', '30 TO 40', '40 TO 50'])][c_cr].sum())
                total_cr = danger_cr + safe_cr
                safe_pct = round((safe_cr / total_cr * 100), 1) if total_cr > 0 else 0.0
                danger_pct = round((danger_cr / total_cr * 100), 1) if total_cr > 0 else 0.0
                shelf_life_composition_shift.append({
                    "month": p_name,
                    "Safe Stock (50-75%+)": round(safe_cr, 1),
                    "Red-Zone Risk (20-50%)": round(danger_cr, 1),
                    "safe_cr": round(safe_cr, 1),
                    "danger_cr": round(danger_cr, 1),
                    "safe_pct": safe_pct,
                    "danger_pct": danger_pct,
                    "total_cr": round(total_cr, 1)
                })

        # Chart 2: Grouped Bar Chart – Category-wise Stock: Start vs. Current Month
        cat_baseline_vs_current = []
        p_first = active_periods[0] if active_periods else None
        p_last = active_periods[-1] if active_periods else None
        df_first = filtered_month_dfs.get(p_first, pd.DataFrame())
        df_last = filtered_month_dfs.get(p_last, pd.DataFrame())

        c_cat_f = [c for c in df_first.columns if c.startswith('Local Category')][1] if len([c for c in df_first.columns if c.startswith('Local Category')]) > 1 else get_col_exact(df_first, ['Local Category', 'Category', 'category'])
        c_cr_f = get_col_exact(df_first, ['Cr', 'CR', 'cr', 'Value'])
        c_cat_l = [c for c in df_last.columns if c.startswith('Local Category')][1] if len([c for c in df_last.columns if c.startswith('Local Category')]) > 1 else get_col_exact(df_last, ['Local Category', 'Category', 'category'])
        c_cr_l = get_col_exact(df_last, ['Cr', 'CR', 'cr', 'Value'])

        first_cat_map = df_first.groupby(c_cat_f)[c_cr_f].sum().to_dict() if c_cat_f and c_cr_f and not df_first.empty else {}
        last_cat_map = df_last.groupby(c_cat_l)[c_cr_l].sum().to_dict() if c_cat_l and c_cr_l and not df_last.empty else {}
        all_cats = list(set(list(first_cat_map.keys()) + list(last_cat_map.keys())))

        for cat in all_cats:
            v_f = float(first_cat_map.get(cat, 0.0))
            v_l = float(last_cat_map.get(cat, 0.0))
            cat_baseline_vs_current.append({
                "category": cat,
                "start_month": p_first,
                "current_month": p_last,
                "start_val": round(float(v_f), 1),
                "current_val": round(float(v_l), 1),
                f"{p_first} (Start)": round(float(v_f), 1),
                f"{p_last} (Current)": round(float(v_l), 1),
                "is_reduced": v_l <= v_f,
                "net_change": round(float(v_l - v_f), 1),
                "_sort_val": v_l + v_f
            })
        cat_baseline_vs_current.sort(key=lambda x: x['_sort_val'], reverse=True)
        for item in cat_baseline_vs_current:
            del item['_sort_val']

        # Chart 3: Grouped Bar Chart – Top Brands: Near-Expiry Exposure (Current Month)
        top_brands_near_expiry = []
        if not df_last.empty:
            c_brand = get_col_exact(df_last, ['IOP', 'Brand', 'brand', 'BRAND'])
            c_cr = get_col_exact(df_last, ['Cr', 'CR', 'cr', 'Value'])
            b_col = get_col_exact(df_last, ['Bucket %', 'bucket %', 'BUCKET %'])
            if c_brand and c_cr and b_col:
                df_last_c = df_last.copy()
                df_last_c['Clean_B'] = df_last_c[b_col].apply(map_to_target_bucket)
                df_last_c['is_red_zone'] = df_last_c['Clean_B'].isin(['20 TO 30', '30 TO 40', '40 TO 50'])
                
                brand_agg = df_last_c.groupby(c_brand).apply(
                    lambda g: pd.Series({
                        'total_cr': float(g[c_cr].sum()),
                        'red_zone_cr': float(g[g['is_red_zone']][c_cr].sum())
                    })
                ).reset_index()
                
                brand_agg = brand_agg[brand_agg['total_cr'] > 0]
                brand_agg['risk_pct'] = brand_agg.apply(
                    lambda r: round((r['red_zone_cr'] / r['total_cr'] * 100), 1) if r['total_cr'] > 0 else 0.0, 
                    axis=1
                )
                brand_agg = brand_agg.sort_values(by=['red_zone_cr', 'total_cr'], ascending=[False, False]).head(7)
                
                for _, r in brand_agg.iterrows():
                    top_brands_near_expiry.append({
                        "brand": str(r[c_brand]),
                        "Total Stock": round(float(r['total_cr']), 1),
                        "Near-Expiry (20-50%)": round(float(r['red_zone_cr']), 1),
                        "total_cr": round(float(r['total_cr']), 1),
                        "red_zone_cr": round(float(r['red_zone_cr']), 1),
                        "risk_pct": float(r['risk_pct'])
                    })

        # Backward compatibility for legacy chart keys
        red_zone_trajectory = []
        for p_name, m_df in filtered_month_dfs.items():
            b_col = get_col_exact(m_df, ['Bucket %', 'bucket %', 'BUCKET %'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if b_col and c_cr and not m_df.empty:
                m_df['Clean_B'] = m_df[b_col].apply(map_to_target_bucket)
                b20 = float(m_df[m_df['Clean_B'] == '20 TO 30'][c_cr].sum())
                b30 = float(m_df[m_df['Clean_B'] == '30 TO 40'][c_cr].sum())
                b40 = float(m_df[m_df['Clean_B'] == '40 TO 50'][c_cr].sum())
                tot_rz = b20 + b30 + b40
                red_zone_trajectory.append({
                    "month": p_name,
                    "Total Red-Zone": round(float(tot_rz), 1),
                    "20% to 30%": round(float(b20), 1),
                    "30% to 40%": round(float(b30), 1),
                    "40% to 50%": round(float(b40), 1),
                    "20 TO 30": round(float(b20), 1),
                    "30 TO 40": round(float(b30), 1),
                    "40 TO 50": round(float(b40), 1)
                })

        liquidation_velocity = []
        for p_name in active_periods:
            m_df = filtered_month_dfs.get(p_name, pd.DataFrame())
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            w_col = get_col_exact(m_df, ['Week', 'week', 'WEEK', 'Wk'])
            cleared_val = 0.0
            if not m_df.empty and c_cr:
                if w_col:
                    unique_w = [str(w).strip() for w in m_df[w_col].dropna().unique()]
                    sorted_w = sort_weeks_list(unique_w)
                    if len(sorted_w) >= 2:
                        w_first = sorted_w[0]
                        w_last = sorted_w[-1]
                        val_w1 = float(m_df[m_df[w_col].astype(str).str.strip() == w_first][c_cr].sum())
                        val_w4 = float(m_df[m_df[w_col].astype(str).str.strip() == w_last][c_cr].sum())
                        cleared_val = val_w4 - val_w1
                    else:
                        cleared_val = 0.0
            
            liquidation_velocity.append({
                "month": p_name,
                "velocity_cr": round(float(cleared_val), 1),
                "is_clearing": cleared_val <= 0
            })

        if all(item["velocity_cr"] == 0.0 for item in liquidation_velocity) and len(active_periods) >= 2:
            month_totals = {p: float(filtered_month_dfs[p][get_col_exact(filtered_month_dfs[p], ['Cr', 'CR', 'cr', 'Value'])].sum()) if (get_col_exact(filtered_month_dfs[p], ['Cr', 'CR', 'cr', 'Value']) and not filtered_month_dfs[p].empty) else 0.0 for p in active_periods}
            liquidation_velocity = []
            for i, p_name in enumerate(active_periods):
                if i == 0:
                    diff = 0.0
                else:
                    prev_p = active_periods[i-1]
                    diff = month_totals.get(p_name, 0.0) - month_totals.get(prev_p, 0.0)
                liquidation_velocity.append({
                    "month": p_name,
                    "velocity_cr": round(float(diff), 1),
                    "is_clearing": diff <= 0
                })

        # Chart backward compatibility
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
                        "value_cr": round(float(r[c_cr]), 1)
                    })

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
                        "value_cr": round(float(r[c_cr]), 1)
                    })

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
                        "value_cr": round(float(r[c_cr]), 1)
                    })

        # Table 1: Category-wise Month-End Stock Trend
        cat_pivots = {}
        for p_name, m_df in filtered_month_dfs.items():
            c_cat = [c for c in m_df.columns if c.startswith('Local Category')][1] if len([c for c in m_df.columns if c.startswith('Local Category')]) > 1 else get_col_exact(m_df, ['Local Category', 'Category', 'category'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if c_cat and c_cr and not m_df.empty:
                cat_pivots[p_name] = m_df.groupby(c_cat)[c_cr].sum()

        cat_matrix_df = pd.DataFrame(cat_pivots).fillna(0)
        cat_matrix = {"columns": [], "rows": []}
        net_col_name = f"Net Change ({p_last} – {p_first})" if len(active_periods) >= 2 else "Net Change"

        if not cat_matrix_df.empty and active_periods:
            avail_cols = [p for p in active_periods if p in cat_matrix_df.columns]
            cat_matrix_df = cat_matrix_df.reindex(columns=avail_cols, fill_value=0)
            
            if len(avail_cols) >= 2:
                cat_matrix_df[net_col_name] = cat_matrix_df[avail_cols[-1]] - cat_matrix_df[avail_cols[0]]
            else:
                cat_matrix_df[net_col_name] = 0.0

            cat_matrix_df = cat_matrix_df.sort_values(by=avail_cols[-1] if avail_cols else cat_matrix_df.columns[0], ascending=False)
            
            total_r = cat_matrix_df[avail_cols].sum().to_frame().T
            total_r.index = ['Total']
            if len(avail_cols) >= 2 and not total_r.empty:
                val_e = float(total_r[avail_cols[-1]].values[0]) if len(total_r[avail_cols[-1]].values) > 0 else 0.0
                val_s = float(total_r[avail_cols[0]].values[0]) if len(total_r[avail_cols[0]].values) > 0 else 0.0
                total_r[net_col_name] = val_e - val_s
            else:
                total_r[net_col_name] = 0.0
            
            final_cat_m = pd.concat([cat_matrix_df, total_r]).reset_index().rename(columns={'index': 'CATEGORY'})
            final_cat_m.columns.name = None
            rows_m = []
            for _, row in final_cat_m.iterrows():
                rec = {}
                for col in final_cat_m.columns:
                    val = row[col]
                    rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
                rows_m.append(rec)
            cat_matrix = {"columns": [str(c) for c in final_cat_m.columns], "rows": rows_m}

        # Table 2: Shelf-Life Risk Concentration Trend
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
                bucket_matrix_df[net_col_name] = bucket_matrix_df[avail_p[-1]] - bucket_matrix_df[avail_p[0]]
            else:
                bucket_matrix_df[net_col_name] = 0.0

            BUCKET_LABELS = {
                '20 TO 30': '20 TO 30 (Critical)',
                '30 TO 40': '30 TO 40 (High Risk)',
                '40 TO 50': '40 TO 50 (Risky)',
                '50 TO 60': '50 TO 60',
                '60 TO 70': '60 TO 70',
                '70 TO 75': '70 TO 75'
            }
            
            # Total Red-Zone (20-50) Row
            rz_indices = [b for b in ['20 TO 30', '30 TO 40', '40 TO 50'] if b in bucket_matrix_df.index]
            red_zone_row = bucket_matrix_df.loc[rz_indices].sum().to_frame().T if rz_indices else pd.DataFrame()
            if not red_zone_row.empty:
                red_zone_row.index = ['Total Red-Zone (20-50)']

            total_b = bucket_matrix_df[avail_p].sum().to_frame().T
            total_b.index = ['Total']
            if len(avail_p) >= 2 and not total_b.empty:
                val_e = float(total_b[avail_p[-1]].values[0]) if len(total_b[avail_p[-1]].values) > 0 else 0.0
                val_s = float(total_b[avail_p[0]].values[0]) if len(total_b[avail_p[0]].values) > 0 else 0.0
                total_b[net_col_name] = val_e - val_s
            else:
                total_b[net_col_name] = 0.0

            bucket_matrix_df.index = [BUCKET_LABELS.get(b, b) for b in bucket_matrix_df.index]
            
            final_b_m = pd.concat([bucket_matrix_df, red_zone_row, total_b]).reset_index().rename(columns={'index': 'SHELF-LIFE BUCKET'})
            final_b_m.columns.name = None
            rows_bm = []
            for _, row in final_b_m.iterrows():
                rec = {}
                for col in final_b_m.columns:
                    val = row[col]
                    rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
                rows_bm.append(rec)
            bucket_matrix = {"columns": [str(c) for c in final_b_m.columns], "rows": rows_bm}

        # Table 3: Top Brands – Cumulative Surplus Trend
        brand_pivots = {}
        for p_name, m_df in filtered_month_dfs.items():
            c_brand = get_col_exact(m_df, ['Brand', 'IOP', 'brand', 'BRAND', 'iop'])
            c_cr = get_col_exact(m_df, ['Cr', 'CR', 'cr', 'Value'])
            if c_brand and c_cr and not m_df.empty:
                brand_pivots[p_name] = m_df.groupby(c_brand)[c_cr].sum()

        brand_matrix_df = pd.DataFrame(brand_pivots).fillna(0)
        brand_surplus_matrix = {"columns": [], "rows": []}
        if not brand_matrix_df.empty and active_periods:
            avail_p = [p for p in active_periods if p in brand_matrix_df.columns]
            brand_matrix_df = brand_matrix_df.reindex(columns=avail_p, fill_value=0)
            if len(avail_p) >= 2:
                brand_matrix_df[net_col_name] = brand_matrix_df[avail_p[-1]] - brand_matrix_df[avail_p[0]]
            else:
                brand_matrix_df[net_col_name] = 0.0

            brand_matrix_df = brand_matrix_df.sort_values(by=avail_p[-1] if avail_p else brand_matrix_df.columns[0], ascending=False).head(10).reset_index().rename(columns={'index': 'BRAND'})
            brand_matrix_df.insert(0, 'RANK', [str(i) for i in range(1, len(brand_matrix_df) + 1)])
            
            rows_brand = []
            for _, row in brand_matrix_df.iterrows():
                rec = {}
                for col in brand_matrix_df.columns:
                    val = row[col]
                    rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
                rows_brand.append(rec)
            brand_surplus_matrix = {"columns": [str(c) for c in brand_matrix_df.columns], "rows": rows_brand}

        # Table 4 / SKU Shelf-Life Breakdown Matrix (matching reference image)
        sku_matrix = build_sku_shelf_life_matrix(df_last if not df_last.empty else (filtered_month_dfs.get(active_periods[0]) if active_periods else pd.DataFrame()))

        escalating_skus = brand_surplus_matrix

        return {
            "mode": mode,
            "is_complete_year": is_complete_year,
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
                "val_end": round(float(val_last), 1),
                "net_4wk_change": round(float(net_change), 1),
                "pct_4wk_growth": round(pct_growth, 1),
                "driver_cat": str(driver_cat),
                "driver_delta": round(float(driver_delta), 1),
                "aging_idx_pct": round(aging_idx_pct, 1),
                "safe_stock_cr": round(float(safe_cr), 1)
            },
            "charts": {
                "shelf_life_composition_shift": shelf_life_composition_shift,
                "cat_baseline_vs_current": cat_baseline_vs_current,
                "top_brands_near_expiry": top_brands_near_expiry,
                "red_zone_trajectory": red_zone_trajectory,
                "liquidation_velocity": liquidation_velocity,
                "cat_evolution": cat_evolution,
                "bucket_migration": bucket_migration,
                "branch_comparison": branch_comparison
            },
            "matrices": {
                "cat_matrix": cat_matrix,
                "bucket_matrix": bucket_matrix,
                "brand_surplus_matrix": brand_surplus_matrix,
                "escalating_skus": brand_surplus_matrix,
                "sku_matrix": sku_matrix
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
            "value_cr": round(float(high_cr), 1),
            "delta_str": delta_str,
            "delta_cr": round(float(delta_high), 1),
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
                "value_cr": round(float(r[c_cr_col]), 1)
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
                "value_cr": round(float(r[c_cr_col]), 1)
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
                "value_cr": round(float(r[c_cr_col]), 1)
            })

    # Table 1: Category-wise Weekly Stock Trend & Table 4: Category-wise Week-over-Week Movement Delta
    cat_matrix = {"columns": [], "rows": []}
    wow_movement = {"columns": [], "rows": []}

    if c_cat_col and c_week_col and c_cr_col and num_active_weeks > 0:
        sub_c_mat = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks)]
        if not sub_c_mat.empty:
            cat_p = sub_c_mat.pivot_table(index=c_cat_col, columns=c_week_col, values=c_cr_col, aggfunc='sum', fill_value=0)
            avail_w = [w for w in active_weeks if w in cat_p.columns]
            cat_p = cat_p.reindex(columns=avail_w, fill_value=0)
            
            w_first = avail_w[0] if avail_w else None
            w_last = avail_w[-1] if avail_w else None

            # Table 1: Category-wise Weekly Stock Trend
            t1_df = cat_p.copy()
            if len(avail_w) >= 2:
                t1_df['Net Change (W4 – W1)'] = t1_df[w_last] - t1_df[w_first]
            else:
                t1_df['Net Change (W4 – W1)'] = 0.0

            t1_df = t1_df.sort_values(by=w_last if w_last else t1_df.columns[0], ascending=False)
            total_t1 = t1_df[avail_w].sum().to_frame().T
            total_t1.index = ['Total']
            if len(avail_w) >= 2 and not total_t1.empty:
                val_e = float(total_t1[w_last].values[0])
                val_s = float(total_t1[w_first].values[0])
                total_t1['Net Change (W4 – W1)'] = val_e - val_s
            else:
                total_t1['Net Change (W4 – W1)'] = 0.0

            final_t1 = pd.concat([t1_df, total_t1]).reset_index().rename(columns={'index': 'CATEGORY', c_cat_col: 'CATEGORY'})
            final_t1.columns.name = None
            rows_t1 = []
            for _, row in final_t1.iterrows():
                rec = {}
                for col in final_t1.columns:
                    val = row[col]
                    rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
                rows_t1.append(rec)
            cat_matrix = {"columns": [str(c) for c in final_t1.columns], "rows": rows_t1}

            # Table 4: Category-wise Week-over-Week Movement Delta
            t4_df = pd.DataFrame(index=cat_p.index)
            if len(avail_w) >= 4:
                t4_df['W2 – W1'] = cat_p[avail_w[1]] - cat_p[avail_w[0]]
                t4_df['W3 – W2'] = cat_p[avail_w[2]] - cat_p[avail_w[1]]
                t4_df['W4 – W3'] = cat_p[avail_w[3]] - cat_p[avail_w[2]]
                t4_df['Net Change (W4 – W1)'] = cat_p[avail_w[3]] - cat_p[avail_w[0]]
            elif len(avail_w) == 3:
                t4_df['W2 – W1'] = cat_p[avail_w[1]] - cat_p[avail_w[0]]
                t4_df['W3 – W2'] = cat_p[avail_w[2]] - cat_p[avail_w[1]]
                t4_df['Net Change (W4 – W1)'] = cat_p[avail_w[2]] - cat_p[avail_w[0]]
            elif len(avail_w) == 2:
                t4_df['W2 – W1'] = cat_p[avail_w[1]] - cat_p[avail_w[0]]
                t4_df['Net Change (W4 – W1)'] = cat_p[avail_w[1]] - cat_p[avail_w[0]]
            else:
                t4_df['Net Change (W4 – W1)'] = 0.0

            t4_df = t4_df.sort_values(by='Net Change (W4 – W1)', ascending=False)
            total_t4 = t4_df.sum().to_frame().T
            total_t4.index = ['Total']
            final_t4 = pd.concat([t4_df, total_t4]).reset_index().rename(columns={'index': 'CATEGORY'})
            final_t4.columns.name = None
            rows_t4 = []
            for _, row in final_t4.iterrows():
                rec = {}
                for col in final_t4.columns:
                    val = row[col]
                    rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
                rows_t4.append(rec)
            wow_movement = {"columns": [str(c) for c in final_t4.columns], "rows": rows_t4}

    # Table 2: Shelf-Life Bucket-wise Weekly Stock Position
    bucket_matrix = {"columns": [], "rows": []}
    if c_bucket_col and c_week_col and c_cr_col and num_active_weeks > 0:
        sub_b_mat = filtered_comp[
            filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks) &
            filtered_comp[c_bucket_col].astype(str).isin(COMPARISON_BUCKETS_ORDER)
        ]
        if not sub_b_mat.empty:
            b_p = sub_b_mat.pivot_table(index=c_bucket_col, columns=c_week_col, values=c_cr_col, aggfunc='sum', fill_value=0)
            avail_w = [w for w in active_weeks if w in b_p.columns]
            b_p = b_p.reindex(columns=avail_w, fill_value=0)
            
            w_first = avail_w[0] if avail_w else None
            w_last = avail_w[-1] if avail_w else None

            if len(avail_w) >= 2:
                b_p['Net Change (W4 – W1)'] = b_p[w_last] - b_p[w_first]
            else:
                b_p['Net Change (W4 – W1)'] = 0.0

            b_p['SortKey'] = [get_bucket_lower(b) or 999 for b in b_p.index]
            b_p = b_p.sort_values('SortKey').drop('SortKey', axis=1)
            
            total_b = b_p[avail_w].sum().to_frame().T
            total_b.index = ['Total']
            if len(avail_w) >= 2 and not total_b.empty:
                val_e = float(total_b[w_last].values[0])
                val_s = float(total_b[w_first].values[0])
                total_b['Net Change (W4 – W1)'] = val_e - val_s
            else:
                total_b['Net Change (W4 – W1)'] = 0.0

            final_b_m = pd.concat([b_p, total_b]).reset_index().rename(columns={'index': 'SHELF-LIFE BUCKET', c_bucket_col: 'SHELF-LIFE BUCKET'})
            final_b_m.columns.name = None
            rows_bm = []
            for _, row in final_b_m.iterrows():
                rec = {}
                for col in final_b_m.columns:
                    val = row[col]
                    rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
                rows_bm.append(rec)
            bucket_matrix = {"columns": [str(c) for c in final_b_m.columns], "rows": rows_bm}

    # Table 3: Top Brands by Surplus Accumulation (W4 vs W1)
    top_brands = {"columns": [], "rows": []}
    if c_brand_col and c_week_col and c_cr_col and num_active_weeks > 0:
        w_first = active_weeks[0]
        w_last = active_weeks[-1]
        
        br_first = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_first)].groupby(c_brand_col)[c_cr_col].sum()
        br_last = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_last)].groupby(c_brand_col)[c_cr_col].sum()
        
        w1_hdr = f"{str(w_first).upper()} (Total CR)" if str(w_first).lower().startswith('week') else f"WEEK {w_first} (Total CR)"
        w4_hdr = f"{str(w_last).upper()} (Total CR)" if str(w_last).lower().startswith('week') else f"WEEK {w_last} (Total CR)"

        br_df = pd.DataFrame({
            w1_hdr: br_first,
            w4_hdr: br_last
        }).fillna(0)
        
        br_df['Net Change (W4 – W1)'] = br_df[w4_hdr] - br_df[w1_hdr]
        br_df = br_df.sort_values(by='Net Change (W4 – W1)', ascending=False).head(10).reset_index().rename(columns={'index': 'BRAND', c_brand_col: 'BRAND'})
        
        br_df.insert(0, 'RANK', [str(i) for i in range(1, len(br_df)+1)])
        rows_br = []
        for _, row in br_df.iterrows():
            rec = {}
            for col in br_df.columns:
                val = row[col]
                rec[str(col)] = round(float(val), 1) if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
            rows_br.append(rec)
        top_brands = {"columns": [str(c) for c in br_df.columns], "rows": rows_br}

    # SKU Shelf-Life Breakdown Matrix (matching reference image)
    sub_sku_df = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks)] if (c_week_col and not filtered_comp.empty) else filtered_comp
    sku_matrix = build_sku_shelf_life_matrix(sub_sku_df)

    sku_watchlist = top_brands
    inter_depot_movement = wow_movement
    escalating_skus = top_brands

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
            "val_end": round(float(val_end), 1),
            "net_4wk_change": round(float(net_4wk), 1),
            "pct_4wk_growth": round(pct_4wk, 1),
            "driver_cat": str(driver_cat),
            "driver_delta": round(float(driver_delta), 1),
            "aging_idx_pct": round(aging_idx_pct, 1),
            "safe_stock_cr": round(float(safe_cr), 1)
        },
        "charts": {
            "cat_evolution": cat_evolution,
            "bucket_migration": bucket_migration,
            "branch_comparison": branch_comparison
        },
        "matrices": {
            "cat_matrix": cat_matrix,
            "bucket_matrix": bucket_matrix,
            "top_brands": top_brands,
            "wow_movement": wow_movement,
            "sku_watchlist": top_brands,
            "inter_depot_movement": wow_movement,
            "escalating_skus": top_brands,
            "sku_matrix": sku_matrix
        }
    }

