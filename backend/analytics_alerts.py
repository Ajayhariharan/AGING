import os
import sys
import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from parser import get_col_exact, get_channel_filter_options
from database import get_stock_df

def calculate_alerts_data(
    depots: Optional[List[str]] = None,
    brands: Optional[List[str]] = None,
    channels: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    depot: Optional[List[str]] = None,
    brand: Optional[List[str]] = None,
    channel: Optional[List[str]] = None,
    risk: Optional[List[str]] = None,
    category: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Computes Aging Alert Views, prioritized SKU alerts, estimated days left, and prescribed action strategies.
    """
    depots = depots or depot or []
    brands = brands or brand or []
    channels = channels or channel or []
    risks = risks or risk or []
    categories = categories or category or []
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
                "value_cr": round(float(cr_val), 1),
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
            "high_risk_value": round(float(total_high), 1),
            "medium_risk_value": round(float(total_medium), 1),
            "high_risk_skus": high_skus,
            "medium_risk_skus": med_skus
        },
        "alerts": alerts_list
    }

