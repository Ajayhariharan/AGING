import io
import re
from typing import Any, Dict, List, Optional
import pandas as pd
from pyxlsb import open_workbook

def clean_col_name(col: Any) -> str:
    if col is None:
        return ""
    c = str(col)
    c = c.replace('\ufeff', '').replace('\u200b', '').replace('\xa0', '')
    return c.strip()

def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x)
    return df

def get_col_exact(df: pd.DataFrame, targets: List[str]) -> Optional[str]:
    col_map = {str(col).strip().lower(): col for col in df.columns}
    for target in targets:
        clean_name = target.strip().lower()
        if clean_name in col_map:
            return col_map[clean_name]
    return None

def parse_week_sort_key(w: Any):
    if pd.isna(w):
        return (9999, 9999, str(w))
    s = str(w).strip()
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    for m_idx, m_name in enumerate(months, start=1):
        if m_name in s.lower():
            day_match = re.search(r'\b(\d{1,2})\b', s)
            day_num = int(day_match.group(1)) if day_match else 1
            return (2024, m_idx, day_num, s)
            
    num_match = re.search(r'\d+', s)
    if num_match:
        return (1000, int(num_match.group(0)), 0, s)
        
    return (2000, 0, 0, s)

def sort_weeks_list(raw_weeks: List[Any]) -> List[str]:
    cleaned = [str(w).strip() for w in raw_weeks if str(w).strip() != '' and str(w).lower() not in ['nan', 'none', 'null', 'total']]
    seen = set()
    unique = []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    try:
        return sorted(unique, key=parse_week_sort_key)
    except Exception:
        return sorted(unique)

def get_bucket_lower(bucket_str: Any) -> Optional[int]:
    if pd.isna(bucket_str):
        return None
    s = str(bucket_str).strip().upper()
    match = re.search(r'>\s*(\d+)', s)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*TO\s*\d+', s)
    if match:
        return int(match.group(1))
    return None

def map_to_target_bucket(val: Any) -> Optional[str]:
    if pd.isna(val):
        return None
    s = str(val).strip().lower().replace(' ', '').replace('-', 'to')
    if '20to30' in s:
        return '20 TO 30'
    elif '30to40' in s:
        return '30 TO 40'
    elif '40to50' in s:
        return '40 TO 50'
    elif '50to60' in s:
        return '50 TO 60'
    elif '60to70' in s:
        return '60 TO 70'
    elif '70to75' in s:
        return '70 TO 75'
    elif '75to80' in s:
        return '75 to 80'
    elif '80to85' in s:
        return '80 to 85'
    return None

TARGET_BUCKETS = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75', '75 to 80']
ALL_BUCKETS_ORDER = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75', '75 to 80', '80 to 85']
STANDARD_BRANCHES = ['01.North', '02.East', '03.West', '04.South']
ALLOWED_BRANCHES = ['01.North', '02.East', '03.West', '04.South', '1.North', '2.East', '3.West', '4.South', 'North', 'East', 'West', 'South']

def normalize_branch_filter(branches: List[str]) -> List[str]:
    if not branches:
        return []
    res = set()
    for b in branches:
        b_str = str(b).strip()
        res.add(b_str)
        if 'North' in b_str:
            res.update(['01.North', '1.North', 'North'])
        elif 'East' in b_str:
            res.update(['02.East', '2.East', 'East'])
        elif 'West' in b_str:
            res.update(['03.West', '3.West', 'West'])
        elif 'South' in b_str:
            res.update(['04.South', '4.South', 'South'])
    return list(res)

def get_channel_filter_options(df_or_vals, col=None):
    if col is not None and isinstance(df_or_vals, pd.DataFrame):
        if col in df_or_vals.columns:
            raw_vals = [str(x).strip() for x in df_or_vals[col].dropna().unique() if str(x).strip() != '']
        else:
            return []
    elif isinstance(df_or_vals, (list, set, tuple, pd.Series)):
        raw_vals = [str(x).strip() for x in df_or_vals if str(x).strip() != '']
    else:
        return []
    
    allowed_order = []
    # 1. 'TT'
    tt_match = [v for v in raw_vals if v.upper() == 'TT' or v.lower() == 'tt']
    if tt_match:
        allowed_order.extend(tt_match)
        
    # 2. 'MT/ E.com / AFH' and other channel values
    mt_match = [
        v for v in raw_vals 
        if ('mt' in v.lower() or 'ecom' in v.lower() or 'afh' in v.lower()) 
        and v.lower() not in ['all channels', 'all channel', 'all', 'expired', '0', '#n/a', '0x2a', 'nan', 'none']
    ]
    if mt_match:
        allowed_order.extend(mt_match)
    
    seen = set()
    result = []
    for item in allowed_order:
        if item not in seen and item.lower() not in ['all channels', 'all channel', 'all', 'nan', 'none']:
            seen.add(item)
            result.append(item)
    return result

def parse_xlsb_bytes(contents: bytes, filename: str) -> Dict[str, pd.DataFrame]:
    sheets = {}
    with open_workbook(io.BytesIO(contents)) as wb:
        for sheetname in wb.sheets:
            with wb.get_sheet(sheetname) as sheet:
                all_rows = []
                for row in sheet.rows():
                    row_data = []
                    for item in row:
                        val = item.v
                        if isinstance(val, bytes):
                            try:
                                val = val.decode('utf-8')
                            except UnicodeDecodeError:
                                val = val.decode('latin-1')
                        row_data.append(val)
                    all_rows.append(row_data)
                
                if all_rows:
                    header_row_index = 0
                    for idx, row in enumerate(all_rows):
                        non_empty = [str(x) for x in row if x is not None and str(x).strip() != '']
                        if len(non_empty) > 0:
                            header_row_index = idx
                            break

                    headers = []
                    for i, col in enumerate(all_rows[header_row_index]):
                        if col is None:
                            headers.append(f"Col_{i}")
                        else:
                            h = col
                            if isinstance(h, bytes):
                                try:
                                    h = h.decode('utf-8')
                                except UnicodeDecodeError:
                                    h = h.decode('latin-1')
                            headers.append(clean_col_name(h))
                    
                    df = pd.DataFrame(all_rows[header_row_index+1:], columns=headers)
                    
                    seen = {}
                    new_cols = []
                    for col in df.columns:
                        if col in seen:
                            seen[col] += 1
                            new_cols.append(f"{col}_{seen[col]}")
                        else:
                            seen[col] = 1
                            new_cols.append(col)
                    df.columns = new_cols
                    df = sanitize_df(df)
                    sheets[sheetname] = df
    return sheets
