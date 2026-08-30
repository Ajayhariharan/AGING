import os
import sys
import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from parser import (
    get_col_exact, get_bucket_lower, map_to_target_bucket,
    STANDARD_BRANCHES, normalize_branch_filter
)
from database import get_stock_df

# User-customized comparison bucket order (only up to 70 TO 75)
COMPARISON_BUCKETS_ORDER = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75']

def calculate_trend_data(dimension: str = "Category", metric: str = "At-Risk Value (Cr)", top_n: Union[int, str] = 10, branches: List[str] = []) -> Dict[str, Any]:
    """
    Computes trajectory time-series, Pareto analysis, shelf-life health profile,
    regional branch breakdown, and strategic leaderboard for the Trend Analysis tab.
    """
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

    # 3. Health Profile (Strictly ordered: 20 TO 30 to 70 to 75)
    comp_data = []
    if chosen_dim_col and t_bucket_col and t_cr_col and target_items:
        comp_df = filtered_tr[
            filtered_tr[chosen_dim_col].isin(target_items[:8]) & 
            filtered_tr['Clean_Bucket'].isin(COMPARISON_BUCKETS_ORDER)
        ]
        if not comp_df.empty:
            comp_pivot = comp_df.pivot_table(index=chosen_dim_col, columns='Clean_Bucket', values=t_cr_col, aggfunc='sum', fill_value=0)
            avail_buckets = [b for b in COMPARISON_BUCKETS_ORDER if b in comp_pivot.columns]
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
        if chosen_dim_col == t_branch_col:
            # If chosen dimension is already Branch, break down by Category
            if t_cat_col:
                br_df = filtered_tr[
                    filtered_tr[t_branch_col].astype(str).isin(['01.North', '02.East', '03.West', '04.South', '1.North', '2.East', '3.West', '4.South', 'North', 'East', 'West', 'South'])
                ]
                if not br_df.empty:
                    br_pivot = br_df.pivot_table(index=t_branch_col, columns=t_cat_col, values=t_cr_col, aggfunc='sum', fill_value=0)
                    for item, row in br_pivot.iterrows():
                        for cat in br_pivot.columns:
                            branch_breakdown_data.append({
                                "item": str(item),
                                "branch": str(cat),
                                "value_cr": round(float(row[cat]), 2)
                            })
        else:
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

