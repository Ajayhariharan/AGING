import streamlit as st
import pandas as pd
from pyxlsb import open_workbook
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="XLSB", layout="wide")

# ---- LIGHT PURPLE PROFESSIONAL THEME CSS (UI ONLY) ----
st.markdown("""
<style>
    /* ===== GLOBAL LIGHT PURPLE THEME VARIABLES ===== */
    :root,
    [data-theme="light"], .stApp[data-theme="light"], [data-testid="stAppViewContainer"][data-theme="light"], .stAppViewContainer[data-theme="light"],
    [data-theme="dark"], .stApp[data-theme="dark"], [data-testid="stAppViewContainer"][data-theme="dark"], .stAppViewContainer[data-theme="dark"] {
        --app-header-color: #2E1065 !important;
        --background-color: #F8F5FC !important;
        --secondary-background-color: #FAF5FF !important;
        --text-color: #2E1065 !important;
        --app-tab-bg: #FAF5FF !important;
        --tbl-border: #DDD6FE !important;
        --tbl-bg: #FFFFFF !important;
        --tbl-text: #1E1B4B !important;
        --tbl-hdr-bg: #7C3AED !important;
        --tbl-hdr-text: #FFFFFF !important;
        --tbl-gt-col-bg: #EDE9FE !important;
        --tbl-gt-col-text: #2E1065 !important;
        --tbl-bg-even: #FFFFFF !important;
        --tbl-bg-odd: #F9F5FF !important;
    }

    /* Force Light Theme Base on Streamlit root and all containers */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], .main > div {
        background-color: #F8F5FC !important;
        color: #2E1065 !important;
    }

    /* Streamlit top header bar */
    header[data-testid="stHeader"], [data-testid="stHeader"] {
        background: #F8F5FC !important;
        background-color: #F8F5FC !important;
        border-bottom: 1px solid #EDE9FE !important;
    }
    header[data-testid="stHeader"] *, [data-testid="stHeader"] * {
        color: #2E1065 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FAF5FF 0%, #F3E8FF 50%, #EDE9FE 100%) !important;
        border-right: 1.5px solid #DDD6FE !important;
    }
    section[data-testid="stSidebar"] * { color: #3B0764 !important; }

    /* Headers adapt to light bg */
    h1, h2, h3, h4 { font-weight: 800; margin-top: 2px !important; margin-bottom: 6px !important; }
    h1 { color: #2E1065 !important; border-bottom: 3px solid #8B5CF6; padding-bottom: 4px; font-size: 26px !important; }
    h2, h3 { font-size: 17px !important; font-weight: 900 !important; color: #4C1D95 !important; }

    /* Widget labels */
    .stMultiSelect label, .stSelectbox label, .stTextInput label,
    .stNumberInput label, .stFileUploader label, .stRadio label,
    .stDownloadButton label { color: #4C1D95 !important; font-weight: 700 !important; }

    /* Metric cards (KPIs) */
    .stMetric {
        background: linear-gradient(135deg, #FFFFFF 0%, #FAF5FF 60%, #F3E8FF 100%) !important;
        padding: 0.65rem !important;
        border-radius: 12px !important;
        border: 1.5px solid #D8B4FE !important;
        box-shadow: 0 4px 14px rgba(124, 58, 237, 0.08) !important;
    }
    div[data-testid="stMetricValue"] { color: #2E1065 !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] { color: #6B21A8 !important; font-weight: 600 !important; }
    div[data-testid="stMetricDelta"] { color: #581C87 !important; }

    /* Compact Spacing */
    .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
    [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

    /* Multiselect and Selectbox Inputs */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1.5px solid #DDD6FE !important;
        border-radius: 8px !important;
        color: #2E1065 !important;
    }
    div[data-baseweb="select"] input {
        color: #2E1065 !important;
    }
    div[data-baseweb="select"] svg {
        fill: #7C3AED !important;
    }
    div[data-baseweb="tag"] {
        background-color: #EDE9FE !important;
        border: 1px solid #C4B5FD !important;
        border-radius: 6px !important;
        color: #4C1D95 !important;
    }
    div[data-baseweb="tag"] * {
        color: #4C1D95 !important;
        font-weight: 600 !important;
    }

    /* All BaseWeb Popovers, Dropdowns, and Listboxes (Dropdown menus) */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    ul[data-baseweb="menu"],
    ul[role="listbox"],
    div[role="listbox"],
    [data-baseweb="select"] ul {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border: 1.5px solid #DDD6FE !important;
        box-shadow: 0 8px 24px rgba(124, 58, 237, 0.15) !important;
        color: #2E1065 !important;
        border-radius: 10px !important;
    }
    li[data-baseweb="menu-item"],
    li[role="option"],
    div[role="option"],
    [data-baseweb="menu"] li {
        background-color: #FFFFFF !important;
        color: #2E1065 !important;
        font-weight: 600 !important;
        padding: 8px 12px !important;
    }
    li[data-baseweb="menu-item"]:hover,
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"],
    [data-baseweb="menu"] li:hover {
        background-color: #EDE9FE !important;
        color: #6D28D9 !important;
    }

    /* Streamlit File Uploader (Light Purple Theme) */
    [data-testid="stFileUploader"],
    [data-testid="stFileUploader"] > section,
    [data-testid="stFileUploaderDropzone"] {
        background-color: #FAF5FF !important;
        background: #FAF5FF !important;
        border: 2px dashed #C4B5FD !important;
        border-radius: 12px !important;
        padding: 16px !important;
    }
    [data-testid="stFileUploader"] *,
    [data-testid="stFileUploaderDropzone"] * {
        color: #2E1065 !important;
    }
    
    /* Browse Files Button (Light Purple) */
    [data-testid="stFileUploader"] button,
    [data-testid="stFileUploader"] button[kind="secondary"],
    [data-testid="stFileUploader"] button[kind="primary"],
    [data-testid="stBaseButton-secondary"] {
        background-color: #EDE9FE !important;
        background: #EDE9FE !important;
        color: #4C1D95 !important;
        border: 1.5px solid #C4B5FD !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 6px rgba(124, 58, 237, 0.08) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stFileUploader"] button:hover,
    [data-testid="stBaseButton-secondary"]:hover {
        background-color: #DDD6FE !important;
        background: #DDD6FE !important;
        border-color: #A855F7 !important;
        color: #2E1065 !important;
    }

    /* When File is Uploaded - Card & Status (Light Purple Theme) */
    [data-testid="stFileUploaderFileData"],
    [data-testid="stFileUploaderFile"],
    div[data-testid="stFileUploaderFileData"] > div {
        background-color: #FAF5FF !important;
        background: #FAF5FF !important;
        border: 1.5px solid #DDD6FE !important;
        border-radius: 10px !important;
        color: #2E1065 !important;
    }
    [data-testid="stFileUploaderFileData"] * {
        color: #2E1065 !important;
    }
    [data-testid="stFileUploaderFileData"] svg,
    [data-testid="stFileUploader"] svg {
        fill: #7C3AED !important;
        color: #7C3AED !important;
    }
    [data-testid="stFileUploaderDeleteBtn"] button {
        background: transparent !important;
        border: none !important;
        color: #6B21A8 !important;
    }
    [data-testid="stFileUploaderDeleteBtn"] button:hover {
        background-color: #EDE9FE !important;
        color: #991B1B !important;
    }
    [data-testid="stFileUploaderProgressBar"] > div {
        background-color: #7C3AED !important;
    }

    /* General Buttons */
    .stButton > button, .stDownloadButton > button {
        background-color: #EDE9FE !important;
        background: #EDE9FE !important;
        color: #4C1D95 !important;
        border: 1.5px solid #C4B5FD !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 8px 18px !important;
        box-shadow: 0 2px 8px rgba(124, 58, 237, 0.1) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #DDD6FE !important;
        background: #DDD6FE !important;
        border-color: #A855F7 !important;
        color: #2E1065 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15) !important;
    }

    /* Modern Pill-Style Tab Bar Container */
    .stTabs [data-baseweb="tab-list"], [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background-color: #EDE9FE !important;
        padding: 6px 10px !important;
        border-radius: 30px !important;
        gap: 8px !important;
        border: 1.5px solid #DDD6FE !important;
        box-shadow: 0 2px 10px rgba(124, 58, 237, 0.08) !important;
        margin-bottom: 16px !important;
        display: inline-flex !important;
    }
    .stTabs [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"], [data-testid="stTabs"] [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* Individual Tab Pill */
    .stTabs [data-baseweb="tab"], [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 20px !important;
        padding: 8px 22px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #581C87 !important; /* Deep visible purple */
        border: none !important;
        background: transparent !important;
        transition: all 0.2s ease-in-out !important;
    }

    /* Hover effect on inactive pills */
    .stTabs [data-baseweb="tab"]:hover, [data-testid="stTabs"] [data-baseweb="tab"]:hover {
        background-color: #DDD6FE !important;
        color: #2E1065 !important;
    }   

    /* Active Selected Pill with Glowing Purple */
    .stTabs [data-baseweb="tab"][aria-selected="true"], [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #7C3AED, #6D28D9) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 14px rgba(109, 40, 217, 0.35) !important;
    }
    
    /* ========================================================= */
    /* SOLID #C084FC PLAIN COLOR HEADERS & TOTAL ROWS FOR TABLES */
    /* ========================================================= */
    
    .styled-custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Target custom table headers with high specificity */
    .styled-custom-table thead,
    .styled-custom-table thead tr,
    .styled-custom-table thead tr th,
    .styled-custom-table th,
    .styled-custom-th,
    [data-testid="stMarkdownContainer"] .styled-custom-table thead th,
    [data-testid="stMarkdownContainer"] .styled-custom-th {
        background-color: #C084FC !important;
        background: #C084FC !important;
        color: #2E1065 !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.6px !important;
        border: 1px solid #A855F7 !important;
        padding: 10px 12px !important;
    }

    /* Target custom table total rows with high specificity */
    .styled-custom-total-tr,
    .styled-custom-total-td,
    .styled-custom-table tr.styled-custom-total-tr,
    .styled-custom-table tr.styled-custom-total-tr td,
    [data-testid="stMarkdownContainer"] .styled-custom-table tr.styled-custom-total-tr td,
    [data-testid="stMarkdownContainer"] .styled-custom-total-td {
        background-color: #C084FC !important;
        background: #C084FC !important;
        color: #2E1065 !important;
        font-weight: 900 !important;
        border: 1px solid #A855F7 !important;
        border-top: 2px solid #8B5CF6 !important;
        padding: 10px 12px !important;
    }
    
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1.5px solid #DDD6FE; box-shadow: 0 4px 10px rgba(124, 58, 237, 0.05); }
    
    /* Target every single dataframe header layer */
    .stDataFrame thead tr th,
    .stDataFrame thead tr th *,
    .stDataFrame [role="columnheader"],
    .stDataFrame [role="columnheader"] *,
    .stDataFrame [data-testid="stHeader"],
    .stDataFrame [data-testid="stHeader"] *,
    .stDataFrame [data-testid="column-header-content"],
    .stDataFrame [data-testid="column-header-content"] *,
    .stDataEditor thead tr th,
    .stDataEditor thead tr th * {
        background: #C084FC !important;
        background-color: #C084FC !important;
        color: #2E1065 !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.6px !important;
        border-bottom: 2px solid #A855F7 !important;
    }
    
    /* Alternating Rows (Light Purple / White) */
    .stDataFrame tbody tr:nth-child(even), .stDataEditor tbody tr:nth-child(even) {
        background-color: #FFFFFF !important;
    }
    .stDataFrame tbody tr:nth-child(odd), .stDataEditor tbody tr:nth-child(odd) {
        background-color: #F9F5FF !important;
    }
    .stDataFrame tbody tr td, .stDataFrame tbody tr td * { color: #1E1B4B !important; }

    /* Checkbox Column formatting */
    .stDataFrame [data-testid="column-header-0"] { min-width: 15px !important; max-width: 15px !important; width: 15px !important; }
    .stDataFrame [data-testid="cell-0-0"] { min-width: 15px !important; max-width: 15px !important; width: 15px !important; padding: 0 !important; }
    .stDataFrame .st-cb { transform: scale(0.7); margin: 0 auto; display: flex; justify-content: center; }


    /* ========================================================= */
    /* SOLID #C084FC HEADERS FOR CUSTOM PIVOT TABLES             */
    /* ========================================================= */
    
    .sticky-pivot-container {
        max-height: 300px;
        overflow-y: auto;
        overflow-x: auto;
        border: 1.5px solid #DDD6FE;
        border-radius: 10px;
        margin-bottom: 20px;
        background-color: #FFFFFF !important;
        box-shadow: 0 4px 10px rgba(124, 58, 237, 0.05);
    }
    .sticky-pivot-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #1E1B4B !important;
        background-color: #FFFFFF !important;
    }
    
    /* Target Pivot Table Headers */
    .sticky-pivot-table thead tr th,
    .sticky-pivot-table thead tr th * {
        background: #C084FC !important;
        background-color: #C084FC !important;
        color: #2E1065 !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        letter-spacing: 0.6px !important;
        border: 1px solid #A855F7 !important;
        padding: 10px 12px !important;
        white-space: nowrap;
    }
    .sticky-pivot-table th.th-left { text-align: left; }
    .sticky-pivot-table th.th-base { text-align: center; }
    .sticky-pivot-table th.th-gt {
        right: 0; z-index: 20;
        text-align: right;
        box-shadow: -2px 0 6px rgba(124, 58, 237, 0.15);
    }

    /* Alternating Rows for Pivot tables */
    .sticky-pivot-table tbody tr:nth-child(even) td {
        background-color: #FFFFFF !important;
    }
    .sticky-pivot-table tbody tr:nth-child(odd) td {
        background-color: #F9F5FF !important;
    }

    .sticky-pivot-table td.td-left {
        padding: 8px 12px; border: 1px solid #E9D5FF;
        text-align: left; font-weight: 600; color: #1E1B4B !important;
        white-space: nowrap;
    }
    .sticky-pivot-table td.td-val {
        padding: 8px 12px; border: 1px solid #E9D5FF;
        text-align: right; color: #1E1B4B !important;
        white-space: nowrap;
    }
    
    /* Grand Total Column */
    .sticky-pivot-table td.td-gt-col {
        position: sticky; right: 0; z-index: 5;
        background: #EDE9FE !important;
        background-color: #EDE9FE !important;
        padding: 8px 12px; border: 1px solid #C4B5FD;
        text-align: right; font-weight: 800 !important; color: #2E1065 !important; 
        white-space: nowrap;
        box-shadow: -2px 0 6px rgba(124, 58, 237, 0.1);
    }
    
    /* SOLID #C084FC TOTAL ROW: FOR BOTTOM GRAND TOTAL ROW */
    .sticky-pivot-table td.tf-left, .sticky-pivot-table td.tf-base, .sticky-pivot-table td.tf-gt {
        position: sticky; bottom: 0; z-index: 10;
        background: #C084FC !important;
        background-color: #C084FC !important; 
        color: #2E1065 !important; 
        font-weight: 900 !important;
        padding: 10px 12px; border: 1px solid #A855F7 !important; border-top: 2px solid #8B5CF6 !important;
        white-space: nowrap;
    }
    .sticky-pivot-table td.tf-left { text-align: left; }
    .sticky-pivot-table td.tf-base { text-align: right; }
    .sticky-pivot-table td.tf-gt {
        right: 0; z-index: 30;
        text-align: right; 
        box-shadow: -2px -2px 6px rgba(124, 58, 237, 0.2);
    }

    /* Pinned Grand Total Bar */
    .gt-bar-container {
        border: 1.5px solid #A855F7;
        border-radius: 0 0 10px 10px; 
        overflow-x: auto; 
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(124, 58, 237, 0.15);
    }
    .gt-bar-table {
        width: 100%; border-collapse: collapse; font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .gt-bar-tr {
        background: #C084FC !important;
        background-color: #C084FC !important; 
    }
    .gt-bar-td, .gt-bar-td-gt {
        background: #C084FC !important;
        background-color: #C084FC !important; 
        color: #2E1065 !important; 
        font-weight: 800 !important;
        padding: 10px 12px; 
        border: 1px solid #A855F7 !important; 
        text-align: center;
    }
    .gt-bar-td-left {
        background: #C084FC !important;
        background-color: #C084FC !important;
        color: #2E1065 !important;
        font-weight: 800 !important;
        padding: 10px 12px; border: 1px solid #A855F7 !important; text-align: left;
    }
    .gt-bar-td-gt {
        position: sticky; right: 0; z-index: 10; 
        box-shadow: -2px 0 6px rgba(124, 58, 237, 0.2);
    }

    /* Alerts specific styling */
    .alert-high { background-color: #fecaca; color: #991b1b; }
    .alert-medium { background-color: #fde68a; color: #92400e; }
</style>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components

components.html("""
<script>
(function() {
    var parentDoc = window.parent.document;
    
    function closeAllPopovers() {
        if (parentDoc.activeElement) {
            parentDoc.activeElement.blur();
        }
        var escEvent = new KeyboardEvent('keydown', {
            key: 'Escape',
            code: 'Escape',
            keyCode: 27,
            which: 27,
            bubbles: true,
            cancelable: true
        });
        parentDoc.dispatchEvent(escEvent);
        if (window.parent) {
            window.parent.dispatchEvent(escEvent);
        }
        var popovers = parentDoc.querySelectorAll('[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"]');
        popovers.forEach(function(p) {
            p.style.display = 'none';
        });
    }

    parentDoc.addEventListener('click', function(e) {
        var opt = e.target.closest('[role="option"], [id*="-option-"], [data-baseweb="menu"] li, [data-baseweb="option"]');
        if (opt) {
            setTimeout(closeAllPopovers, 40);
            setTimeout(closeAllPopovers, 120);
        }
    }, true);
})();
</script>
""", height=0, width=0)

st.title("Aging Dashboard")

def clean_col_name(col):
    if col is None:
        return ""
    c = str(col)
    c = c.replace('\ufeff', '').replace('\u200b', '').replace('\xa0', '')
    return c.strip()

# Helper function to find a column name ignoring case
def get_col(df, target):
    for col in df.columns:
        if target.lower() in str(col).lower():
            return col
    return None

def get_col_exact(df, targets):
    col_map = {str(col).strip().lower(): col for col in df.columns}
    for target in targets:
        clean_name = target.strip().lower()
        if clean_name in col_map:
            return col_map[clean_name]
    return None

def get_bucket_lower(bucket_str):
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

def get_channel_filter_options(df_or_vals, col=None):
    if col is not None and isinstance(df_or_vals, pd.DataFrame):
        if col in df_or_vals.columns:
            raw_vals = [str(x).strip() for x in df_or_vals[col].dropna().unique() if str(x).strip() != '']
        else:
            return []
    elif isinstance(df_or_vals, (list, set, tuple, pd.Series, np.ndarray)):
        raw_vals = [str(x).strip() for x in df_or_vals if str(x).strip() != '']
    else:
        return []
    
    allowed_order = []
    # 1. 'All Channels'
    all_ch = [v for v in raw_vals if v.lower() == 'all channels' or (('all' in v.lower()) and ('channel' in v.lower()))]
    if all_ch:
        allowed_order.extend(all_ch)
    
    # 2. 'TT'
    tt_match = [v for v in raw_vals if v.upper() == 'TT' or v.lower() == 'tt']
    if tt_match:
        allowed_order.extend(tt_match)
        
    # 3. 'MT/ E.com / AFH' and MT/Ecom/AFH options
    mt_match = [v for v in raw_vals if ('mt' in v.lower() or 'ecom' in v.lower() or 'afh' in v.lower()) and v not in allowed_order and v.lower() not in ['expired', '0', '#n/a', '0x2a']]
    if mt_match:
        allowed_order.extend(mt_match)
    
    seen = set()
    result = []
    for item in allowed_order:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def safe_styler_map(styler, func, subset=None):
    if hasattr(styler, 'map'):
        return styler.map(func, subset=subset)
    return styler.applymap(func, subset=subset)

def render_styled_table(df, max_height=None):
    if df is None or df.empty:
        return
    
    headers = [str(c) for c in df.columns]
    
    rows_html = []
    for idx, row in df.iterrows():
        is_total = any(str(v).strip().lower() == 'total' for v in row.values)
        if is_total:
            tr_style = "background-color: #C084FC !important; background: #C084FC !important; color: #2E1065 !important; font-weight: 900; border-top: 2px solid #8B5CF6;"
            td_style_base = "background-color: #C084FC !important; background: #C084FC !important; padding: 10px 12px; font-size: 13px; color: #2E1065 !important; font-weight: 900; border: 1px solid #A855F7;"
            tr_class = "styled-custom-total-tr"
        else:
            bg = "#FFFFFF" if idx % 2 == 0 else "#FAF5FF"
            tr_style = f"background-color: {bg} !important; background: {bg} !important;"
            td_style_base = f"background-color: {bg} !important; background: {bg} !important; padding: 8px 12px; font-size: 13px; color: #1E1B4B !important; border: 1px solid #EDE9FE;"
            tr_class = ""

        tds = []
        for col_name, val in zip(headers, row.values):
            align = "right" if isinstance(val, (int, float)) or (isinstance(val, str) and (val.endswith('%') or (val.replace('.', '', 1).replace('-', '', 1).replace('+', '', 1).isdigit()))) else "left"
            if isinstance(val, float):
                formatted_val = f"{val:,.4f}" if ('Cr' in col_name or 'Lac' in col_name or 'Value' in col_name) else f"{val:,.2f}"
            elif val is None or pd.isna(val):
                formatted_val = ""
            else:
                formatted_val = str(val)
            
            if is_total:
                tds.append(f'<td class="styled-custom-total-td" style="{td_style_base} text-align: {align};">{formatted_val}</td>')
            else:
                if col_name.lower() in ['risk', 'risk level'] and formatted_val == 'High':
                    tds.append(f'<td style="{td_style_base} text-align: {align}; background-color: #FECACA !important; background: #FECACA !important; color: #991B1B !important; font-weight: 700;">{formatted_val}</td>')
                elif col_name.lower() in ['risk', 'risk level'] and formatted_val == 'Medium':
                    tds.append(f'<td style="{td_style_base} text-align: {align}; background-color: #FEF08A !important; background: #FEF08A !important; color: #854D0E !important; font-weight: 700;">{formatted_val}</td>')
                else:
                    tds.append(f'<td style="{td_style_base} text-align: {align};">{formatted_val}</td>')
        
        rows_html.append(f'<tr class="{tr_class}" style="{tr_style}">{"".join(tds)}</tr>')
    
    ths = []
    for col_name in headers:
        align = "right" if any(k in col_name for k in ['Lac', 'Cr', 'Share', 'Growth', 'Stock', '%', 'Change', 'Surge', 'Days']) else "left"
        ths.append(f'<th class="styled-custom-th" style="background-color: #C084FC !important; background: #C084FC !important; color: #2E1065 !important; font-weight: 800; font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px; padding: 10px 12px; text-align: {align}; border: 1px solid #A855F7; white-space: nowrap;">{col_name}</th>')
    
    table_html = f"""
    <div style="border: 1.5px solid #DDD6FE; border-radius: 10px; overflow-x: auto; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.06); {f'max-height: {max_height}px; overflow-y: auto;' if max_height else ''}">
        <table class="styled-custom-table" style="width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;">
            <thead style="position: sticky; top: 0; z-index: 10; background-color: #C084FC !important; background: #C084FC !important;"><tr>{"".join(ths)}</tr></thead>
            <tbody>{"".join(rows_html)}</tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

# --- FIX: FORCE COLORS STRICTLY ON GRAND TOTAL COLUMN ---
def process_and_style_pivot(pivot_df, target_cols, key=None, height=360):
    if pivot_df.empty:
        return
    
    index_name = pivot_df.index.name or (pivot_df.index.names[0] if pivot_df.index.names else 'Index')
    
    # 1. Flatten the MultiIndex pivot table FIRST
    flat_df = pivot_df.reset_index()
    index_cols = list(flat_df.columns[:len(pivot_df.index.names)])
    
    # 2. Find the numeric columns that match our target bucket columns
    numeric_cols_flat = flat_df.select_dtypes(include=['number']).columns
    target_cols_upper = [str(c).upper().strip() for c in target_cols]
    
    visible_numeric_cols = [c for c in numeric_cols_flat if str(c).upper().strip() in target_cols_upper]
    visible_numeric_cols.sort(key=lambda c: target_cols_upper.index(str(c).upper().strip()) if str(c).upper().strip() in target_cols_upper else 999)
    
    # 3. Calculate GRAND TOTAL row-by-row on the FLAT dataframe
    flat_df['GRAND TOTAL'] = flat_df[visible_numeric_cols].sum(axis=1)
    
    # 4. Keep strictly the columns we want
    final_cols = index_cols + visible_numeric_cols + ['GRAND TOTAL']
    flat_df = flat_df[final_cols]
    
    # 5. Sort and limit to top 10
    flat_df = flat_df.sort_values(by='GRAND TOTAL', ascending=False).head(10)

    # 6. Force light purple background & deep purple text strictly on the GRAND TOTAL column
    def style_grand_total(val):
        return 'background-color: #EDE9FE !important; font-weight: 800 !important; color: #2E1065 !important;'

    # 7. Format only the numeric columns (preventing ValueError for strings)
    numeric_cols_to_format = visible_numeric_cols + ['GRAND TOTAL']
    
    styled_df = safe_styler_map(flat_df.style, style_grand_total, subset=pd.IndexSlice[:, 'GRAND TOTAL']).format(
        "{:,.2f}", 
        subset=numeric_cols_to_format
    ).set_table_styles([
        {'selector': 'thead th', 'props': [('background', 'linear-gradient(135deg, #6B21A8, #7C3AED)'), ('background-color', '#6B21A8'), ('color', '#FFFFFF'), ('font-weight', '800'), ('text-transform', 'uppercase'), ('font-size', '12px'), ('letter-spacing', '0.6px'), ('border-bottom', '2px solid #581C87')]},
        {'selector': 'th, td', 'props': [('border', '1px solid #E9D5FF'), ('text-align', 'center'), ('padding', '8px')]}
    ])

    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True,
        height=height,
        key=key
    )

    # Pinned Grand Total Bar (Bold Purple Theme) - Avoid summing string columns
    gt_vals = {index_name: "Grand Total"}
    for c in visible_numeric_cols:
        gt_vals[c] = round(flat_df[c].sum(), 2)
    gt_vals['GRAND TOTAL'] = round(flat_df['GRAND TOTAL'].sum(), 2)

    gt_tds = ""
    for c in visible_numeric_cols:
        val = gt_vals[c]
        gt_tds += f'<td class="gt-bar-td">{val:,.2f}</td>'

    gt_total_val = gt_vals["GRAND TOTAL"]
    gt_html = f'''
    <div class="gt-bar-container">
        <table class="gt-bar-table">
            <tr class="gt-bar-tr">
                <td class="gt-bar-td-left">Grand Total</td>
                {gt_tds}
                <td class="gt-bar-td-gt">{gt_total_val:,.2f}</td>
            </tr>
        </table>
    </div>
    '''
    st.markdown(gt_html, unsafe_allow_html=True)

@st.cache_data
def load_sheets(uploaded_file):
    sheets = {}
    with open_workbook(uploaded_file) as wb:
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

                    # Sanitize mixed object/bytes types for PyArrow compatibility
                    for col in df.columns:
                        if df[col].dtype == 'object':
                            df[col] = df[col].apply(lambda x: x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x)
                    
                    sheets[sheetname] = df
    return sheets

with st.sidebar:
    uploaded_file = st.file_uploader("Upload an .xlsb file", type=['xlsb'])
    if uploaded_file is not None:
        with st.spinner("Loading file..."):
            sheets = load_sheets(uploaded_file)
            if not sheets:
                st.warning("No sheets found.")
                st.stop()
            st.success(f"Loaded {len(sheets)} sheet(s).")

if uploaded_file is not None:
    # Pre-resolve stock sheet so all tabs have reliable access
    stock_df = None
    for sname, s_df in sheets.items():
        if 'master' not in sname.lower():
            stock_df = s_df.copy()
            break
    if stock_df is None and len(sheets) > 0:
        stock_df = list(sheets.values())[0].copy()

    tab_names = list(sheets.keys())
    tab_names.append("Dashboard")
    tab_names.append("Alert View")
    tab_names.append("Comparison")
    tab_names.append("Trend Analysis")
    tabs = st.tabs(tab_names)

    # Plotly Light Purple Theme Styler
    def apply_dark_theme(fig, height=380, title=None):
        # Extract title safely without turning into 'undefined'
        chart_title = title
        if not chart_title and hasattr(fig, 'layout') and fig.layout.title and hasattr(fig.layout.title, 'text') and fig.layout.title.text:
            chart_title = fig.layout.title.text
        
        layout_dict = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(250, 245, 255, 0.7)",
            font=dict(color="#2E1065", family="Segoe UI, Roboto, sans-serif"),
            margin=dict(l=30, r=30, t=50 if chart_title else 30, b=40),
            height=height,
            legend=dict(
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="rgba(196, 181, 253, 0.6)",
                borderwidth=1,
                font=dict(color="#2E1065", size=11)
            ),
            xaxis=dict(
                gridcolor="rgba(196, 181, 253, 0.4)",
                zerolinecolor="rgba(168, 85, 247, 0.6)",
                tickfont=dict(color="#4C1D95", size=11),
                title_font=dict(color="#2E1065", size=12)
            ),
            yaxis=dict(
                gridcolor="rgba(196, 181, 253, 0.4)",
                zerolinecolor="rgba(168, 85, 247, 0.6)",
                tickfont=dict(color="#4C1D95", size=11),
                title_font=dict(color="#2E1065", size=12)
            ),
            hoverlabel=dict(
                bgcolor="#7C3AED",
                font_size=12,
                font_family="Segoe UI, Roboto, sans-serif",
                font_color="#FFFFFF"
            )
        )
        if chart_title:
            layout_dict['title'] = dict(
                text=str(chart_title),
                font=dict(color="#2E1065", size=15, family="Segoe UI, Roboto, sans-serif")
            )
        fig.update_layout(**layout_dict)
        return fig


    for tab, tab_name in zip(tabs, tab_names):
        # ---- DASHBOARD TAB LOGIC ----
        if tab_name == "Dashboard":
            with tab:
                if stock_df is None:
                    st.warning("No stock sheet data available to generate the dashboard. Please ensure the file has a non-Master sheet with stock data.")
                else:
                    dashboard_df = stock_df.copy()

                    d_week_col = get_col_exact(dashboard_df, ['Week', 'week', 'WEEK', 'Wk'])
                    d_branch_col = get_col_exact(dashboard_df, ['Branch', 'branch', 'BRANCH'])
                    d_mt_col = get_col_exact(dashboard_df, ['MT', 'mt', 'Channel', 'channel'])
                    d_bucket_col = get_col_exact(dashboard_df, ['Bucket %', 'bucket %', 'BUCKET %'])
                    
                    d_brand_col = get_col_exact(dashboard_df, ['IOP', 'Brand', 'Material Description', 'brand', 'BRAND'])
                    
                    local_cat_cols = [c for c in dashboard_df.columns if c.startswith('Local Category')]
                    if len(local_cat_cols) > 1:
                        d_cat_col = local_cat_cols[1]
                    else:
                        d_cat_col = get_col_exact(dashboard_df, ['Local Category', 'Category', 'category', 'CATEGORY'])
                    
                    d_link_col = get_col_exact(dashboard_df, ['link des', 'link_des', 'Link des'])
                    d_cr_col = get_col_exact(dashboard_df, ['Cr', 'CR', 'cr'])
                    
                    d_depot_code_col = get_col_exact(dashboard_df, ['Depot Code', 'Depot code', 'DEPOT CODE'])
                    d_bucket_days_col = get_col_exact(dashboard_df, ['Bucket of days', 'bucket of days', 'BUCKET OF DAYS'])

                    # Pivot Filtering Controls
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        if d_week_col:
                            week_vals = sorted(set(str(x) for x in dashboard_df[d_week_col].dropna().unique()))
                        else:
                            week_vals = []
                        selected_week = st.multiselect("Week", week_vals, default=[], key="dash_week")
                    with col_f2:
                        if d_branch_col:
                            branch_vals = sorted(set(str(x) for x in dashboard_df[d_branch_col].dropna().unique()))
                            allowed_branches = ['01.North', '02.East', '03.West', '04.South']
                            branch_vals = [v for v in branch_vals if v in allowed_branches]
                        else:
                            branch_vals = []
                        selected_branch = st.multiselect("Branch", branch_vals, default=[], key="dash_branch")
                    with col_f3:
                        if d_mt_col:
                            channel_vals = get_channel_filter_options(dashboard_df, d_mt_col)
                        else:
                            channel_vals = []
                        selected_channel = st.multiselect("Channel (MT)", channel_vals, default=[], key="dash_channel")

                    if d_week_col and selected_week:
                        dashboard_df = dashboard_df[dashboard_df[d_week_col].astype(str).isin(selected_week)]
                    if d_branch_col and selected_branch:
                        dashboard_df = dashboard_df[dashboard_df[d_branch_col].astype(str).isin(selected_branch)]
                    if d_mt_col and selected_channel:
                        dashboard_df = dashboard_df[dashboard_df[d_mt_col].astype(str).isin(selected_channel)]

                    if d_cr_col:
                        dashboard_df[d_cr_col] = pd.to_numeric(dashboard_df[d_cr_col], errors='coerce').fillna(0)

                    # ---- RISK CARDS ----
                    col1, col2 = st.columns(2)
                    if d_bucket_col and d_cr_col:
                        d_bucket_lower_map = {b: get_bucket_lower(b) for b in dashboard_df[d_bucket_col].dropna().unique()}
                        d_lower_series = dashboard_df[d_bucket_col].map(d_bucket_lower_map)

                        high_risk_mask = (d_lower_series >= 20) & (d_lower_series < 50)
                        med_risk_mask = (d_lower_series >= 50) & (d_lower_series < 75)

                        high_risk_val = dashboard_df[high_risk_mask][d_cr_col].sum()
                        med_risk_val = dashboard_df[med_risk_mask][d_cr_col].sum()
                    else:
                        high_risk_val, med_risk_val = 0, 0

                    with col1:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #ef4444, #dc2626); min-height: 125px; padding: 6px; border-radius: 12px; text-align: center; color: white; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2); display: flex; flex-direction: column; justify-content: center; align-items: center;">
                            <h4 style="color: white !important;  font-size: 24px; font-weight: 700; letter-spacing: 0.8px;">HIGH RISK</h4>
                            <div style="color:white; font-size:48px; font-weight:900; line-height:1; margin:4px 0;">{high_risk_val:,.2f} Cr</div>
                            <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 12px; font-weight: 500;">Total amount (20%-50%)</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #f59e0b, #d97706); min-height: 125px; padding: 6px; border-radius: 12px; text-align: center; color: white; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2); display: flex; flex-direction: column; justify-content: center; align-items: center;">
                            <h4 style="color: white !important;  font-size: 24px; font-weight: 700; letter-spacing: 0.8px;">MEDIUM RISK</h4>
                            <div style="color:white; font-size:48px; font-weight:900; line-height:1; margin:4px 0;">{med_risk_val:,.2f} Cr</div>
                            <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 12px; font-weight: 500;">Total amount (50%-75%)</p>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")
                    
                    # Target bucket normalization function
                    def map_to_target_bucket(val):
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
                        return None

                    target_buckets = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75', '75 to 80']
                    if d_bucket_col:
                        dashboard_df['Target_Bucket'] = dashboard_df[d_bucket_col].apply(map_to_target_bucket)
                    else:
                        dashboard_df['Target_Bucket'] = None

                    # ==========================================================
                    # REVISED LAYOUT: Two stacked columns to eliminate gaps
                    # ==========================================================
                    
                    # Define the two columns
                    col_left, col_right = st.columns(2)

                    # =========== LEFT COLUMN (Tables 1, 4, 5) ===========
                    with col_left:
                        # -------- TABLE 1: AT-RISK BY CATEGORY --------
                        st.subheader("AT-RISK BY CATEGORY")
                        if d_cat_col and d_cr_col and d_bucket_col:
                            cat_filtered = dashboard_df[dashboard_df['Target_Bucket'].notna()]
                            if not cat_filtered.empty:
                                cat_pivot = cat_filtered.pivot_table(
                                    index=d_cat_col, 
                                    columns='Target_Bucket', 
                                    values=d_cr_col, 
                                    aggfunc='sum', 
                                    fill_value=0
                                )
                                cat_pivot = cat_pivot.reindex(columns=target_buckets, fill_value=0)
                                cat_pivot['Row_Total'] = cat_pivot[target_buckets].sum(axis=1)
                                grand_cat_total = cat_pivot['Row_Total'].sum()
                                if grand_cat_total > 0:
                                    cat_pivot['Share'] = ((cat_pivot['Row_Total'] / grand_cat_total) * 100).round(0).astype(int).astype(str) + '%'
                                else:
                                    cat_pivot['Share'] = '0%'
                                cat_pivot = cat_pivot.sort_values(by='Row_Total', ascending=False).drop(columns=['Row_Total'])
                                
                                total_row = cat_pivot[target_buckets].sum().to_frame().T
                                total_row.index = ['Total']
                                total_row['Share'] = '100%'
                                
                                final_cat_pivot = pd.concat([cat_pivot, total_row]).reset_index().rename(columns={'index': 'Category', d_cat_col: 'Category'})
                                final_cat_pivot.columns.name = None
                                render_styled_table(final_cat_pivot)
                            else:
                                st.info("No data found for the selected risk buckets in Category.")
                        else:
                            st.info("Columns 'Local Category', 'Bucket %', or 'Cr' missing.")

                        st.markdown("---")

                        # -------- TABLE 5: AT-RISK BY BRANCH x CATEGORY --------
                        st.subheader("AT-RISK BY BRANCH x CATEGORY (Lac)")
                        if d_branch_col and d_cat_col and d_cr_col:
                            allowed_branches = ['1.North', '2.East', '3.West', '4.South', 
                                                '01.North', '02.East', '03.West', '04.South',
                                                'North', 'East', 'West', 'South', 'Factory']
                            filtered_branch_df = dashboard_df[dashboard_df[d_branch_col].astype(str).str.strip().isin(allowed_branches)]

                            branch_cat_pivot = filtered_branch_df.pivot_table(
                                index=d_branch_col, 
                                columns=d_cat_col, 
                                values=d_cr_col, 
                                aggfunc='sum', 
                                fill_value=0
                            )
                            branch_cat_pivot['Total'] = branch_cat_pivot.sum(axis=1)
                            total_row = branch_cat_pivot.sum().to_frame().T
                            total_row.index = ['Total']
                            branch_cat_pivot = pd.concat([branch_cat_pivot, total_row])
                            
                            final_pivot = branch_cat_pivot.reset_index().rename(columns={d_branch_col: 'Branch'})
                            render_styled_table(final_pivot)
                        else:
                            st.info("Columns 'Branch', 'Local Category', or 'Cr' missing.")

                    # =========== RIGHT COLUMN (Tables 2, 3, 6) ===========
                    with col_right:
                        # -------- TABLE 2: TOP 10 BRANDS --------
                        st.subheader("TOP 10 BRANDS")
                        if d_brand_col and d_cr_col and d_bucket_col:
                            brand_filtered = dashboard_df[dashboard_df['Target_Bucket'].notna()]
                            if not brand_filtered.empty:
                                brand_pivot = brand_filtered.pivot_table(
                                    index=d_brand_col, 
                                    columns='Target_Bucket', 
                                    values=d_cr_col, 
                                    aggfunc='sum', 
                                    fill_value=0
                                )
                                brand_pivot = brand_pivot.reindex(columns=target_buckets, fill_value=0)
                                brand_pivot['Row_Total'] = brand_pivot[target_buckets].sum(axis=1)
                                all_brand_total = brand_pivot['Row_Total'].sum()
                                brand_pivot = brand_pivot.sort_values(by='Row_Total', ascending=False).head(10)
                                if all_brand_total > 0:
                                    brand_pivot['Share'] = ((brand_pivot['Row_Total'] / all_brand_total) * 100).round(0).astype(int).astype(str) + '%'
                                else:
                                    brand_pivot['Share'] = '0%'
                                
                                total_row = brand_pivot[target_buckets].sum().to_frame().T
                                total_row.index = ['Total']
                                top10_sum = brand_pivot['Row_Total'].sum()
                                total_row['Share'] = f"{int(round((top10_sum / all_brand_total * 100)))}%" if all_brand_total > 0 else "100%"
                                
                                brand_pivot = brand_pivot.drop(columns=['Row_Total'])
                                
                                final_brand_pivot = pd.concat([brand_pivot, total_row]).reset_index().rename(columns={'index': 'Brand', d_brand_col: 'Brand'})
                                final_brand_pivot.columns.name = None
                                final_brand_pivot.insert(0, '#', [str(i) if i < len(final_brand_pivot) else '' for i in range(1, len(final_brand_pivot)+1)])
                                render_styled_table(final_brand_pivot)
                            else:
                                st.info("No data found for the selected risk buckets in Brands.")
                        else:
                            st.info("Columns 'Brand', 'Bucket %', or 'Cr' missing.")

                        st.markdown("---")

                        # -------- TABLE 3: AT-RISK BY BRANCH --------
                        st.subheader("AT-RISK BY BRANCH")
                        if d_branch_col and d_cr_col and d_bucket_col:
                            allowed_branches = ['1.North', '2.East', '3.West', '4.South', 
                                                '01.North', '02.East', '03.West', '04.South',
                                                'North', 'East', 'West', 'South', 'Factory']
                            filtered_branch_df = dashboard_df[
                                dashboard_df[d_branch_col].astype(str).str.strip().isin(allowed_branches) &
                                dashboard_df['Target_Bucket'].notna()
                            ]
                            
                            if not filtered_branch_df.empty:
                                branch_pivot = filtered_branch_df.pivot_table(
                                    index=d_branch_col, 
                                    columns='Target_Bucket', 
                                    values=d_cr_col, 
                                    aggfunc='sum', 
                                    fill_value=0
                                )
                                branch_pivot = branch_pivot.reindex(columns=target_buckets, fill_value=0)
                                branch_pivot['Row_Total'] = branch_pivot[target_buckets].sum(axis=1)
                                grand_branch_total = branch_pivot['Row_Total'].sum()
                                if grand_branch_total > 0:
                                    branch_pivot['Share'] = ((branch_pivot['Row_Total'] / grand_branch_total) * 100).round(0).astype(int).astype(str) + '%'
                                else:
                                    branch_pivot['Share'] = '0%'
                                branch_pivot = branch_pivot.sort_values(by='Row_Total', ascending=False).drop(columns=['Row_Total'])
                                
                                total_row = branch_pivot[target_buckets].sum().to_frame().T
                                total_row.index = ['Total']
                                total_row['Share'] = '100%'
                                
                                final_branch_pivot = pd.concat([branch_pivot, total_row]).reset_index().rename(columns={'index': 'Branch', d_branch_col: 'Branch'})
                                final_branch_pivot.columns.name = None
                                render_styled_table(final_branch_pivot)
                            else:
                                st.info("No data found for the selected risk buckets in Branch.")
                        else:
                            st.info("Columns 'Branch', 'Bucket %', or 'Cr' missing.")

                        st.markdown("---")

                    st.markdown("---")

                    # -------- TABLE 7: IWO REBALANCING HEATMAP (Full width) --------
                    st.subheader("IWO Rebalancing - Near-Ageing Stock by DC")
                    if d_link_col and d_depot_code_col and d_cr_col:
                        sku_agg_hm = dashboard_df.groupby(d_link_col)[d_cr_col].sum().reset_index()
                        top_10_skus = sku_agg_hm.sort_values(d_cr_col, ascending=False).head(10)[d_link_col].tolist()

                        heatmap_df = dashboard_df[dashboard_df[d_link_col].isin(top_10_skus)]

                        if not heatmap_df.empty:
                            target_depots_order = [
                                'IN5H', 'IN6D', 'IN5G', 'IN5F', 'IN5C', 'IN5D',  # North
                                'IN6Z', 'IN6B', 'IN6F', 'IN6G', 'IN5V', 'IN5R',  # East
                                'IN7B', 'IN8K', 'IN7H', 'IN7D', 'IN8G', 'IN7A', 'IN8L', # West
                                'IN7E', 'IN8Y', 'IN7T', 'IN8V', 'IN7Z', 'IN8R', 'IN7C', # South
                                'IN34', 'IN19' # Factory
                            ]
                            
                            heatmap_df = heatmap_df[heatmap_df[d_depot_code_col].isin(target_depots_order)]

                            heatmap_pivot = heatmap_df.pivot_table(
                                index=d_link_col,
                                columns=d_depot_code_col,
                                values=d_cr_col,
                                aggfunc='sum',
                                fill_value=0
                            )
                            
                            available_cols = [c for c in target_depots_order if c in heatmap_pivot.columns]
                            heatmap_pivot = heatmap_pivot.reindex(columns=available_cols)
                            heatmap_pivot.columns.name = None

                            flat_hm = heatmap_pivot.reset_index().rename(columns={d_link_col: 'LINK DES'})

                            styled_heatmap = flat_hm.style.background_gradient(
                                subset=available_cols, cmap='YlOrRd', axis=None
                            ).format(
                                "{:,.2f}", subset=available_cols
                            ).hide(axis='index').set_table_styles([
                                {'selector': 'thead th', 'props': [
                                    ('background-color', '#C084FC !important'), 
                                    ('background', '#C084FC !important'),
                                    ('color', '#2E1065 !important'), 
                                    ('font-weight', '800 !important'), 
                                    ('border', '1px solid #A855F7 !important'), 
                                    ('text-transform', 'uppercase !important'), 
                                    ('font-size', '12px !important'), 
                                    ('padding', '10px 12px !important'), 
                                    ('letter-spacing', '0.6px !important'),
                                    ('position', 'sticky !important'),
                                    ('top', '0 !important'),
                                    ('z-index', '10 !important')
                                ]},
                                {'selector': 'tbody td:first-child', 'props': [
                                    ('background-color', '#FFFFFF !important'), 
                                    ('background', '#FFFFFF !important'),
                                    ('color', '#1E1B4B !important'), 
                                    ('font-weight', '700 !important'), 
                                    ('border', '1px solid #EDE9FE !important'), 
                                    ('padding', '8px 12px !important'), 
                                    ('text-align', 'left !important'),
                                    ('white-space', 'nowrap !important')
                                ]},
                                {'selector': 'tbody td', 'props': [
                                    ('border', '1px solid #EDE9FE !important'), 
                                    ('padding', '8px 12px !important'), 
                                    ('text-align', 'right !important'), 
                                    ('font-size', '13px !important'),
                                    ('white-space', 'nowrap !important')
                                ]},
                                {'selector': 'table', 'props': [
                                    ('width', '100% !important'),
                                    ('border-collapse', 'collapse !important'),
                                    ('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important')
                                ]}
                            ])
                            
                            hm_html = f"""
                            <div style="border: 1.5px solid #DDD6FE; border-radius: 10px; overflow-x: auto; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.06); max-height: 450px; overflow-y: auto;">
                                {styled_heatmap.to_html()}
                            </div>
                            """
                            st.markdown(hm_html, unsafe_allow_html=True)
                        else:
                            st.info("No data available for the Top 10 SKUs Heatmap.")
                    else:
                        st.info("Columns 'SKU', 'Depot Code', or 'Cr' missing for Heatmap.")

            continue

        # ---- ALERTS TAB LOGIC ----
        elif tab_name == "Alert View":
            with tab:
                st.subheader("Shelf-Life Alerts")
                st.caption("Identifies products with low remaining shelf life and recommends actions.")

                if stock_df is None:
                    st.warning("No stock data available. Please ensure the uploaded file contains a non-Master sheet with stock information.")
                else:
                    alerts_df = stock_df.copy()

                    bucket_col = get_col_exact(alerts_df, ['Bucket %', 'bucket %', 'BUCKET %'])
                    brand_col = get_col_exact(alerts_df, ['IOP', 'Brand', 'brand', 'BRAND'])
                    depot_col = get_col_exact(alerts_df, ['Depot', 'Depot Code', 'depot', 'DEPOT'])
                    material_col = get_col_exact(alerts_df, ['Material Code', 'Material code', 'MATERIAL CODE'])
                    sku_desc_col = get_col_exact(alerts_df, ['SKU Des', 'SKU Description', 'link des', 'Link des'])
                    cr_col = get_col_exact(alerts_df, ['Cr', 'CR', 'cr'])
                    stock_col = get_col_exact(alerts_df, ['Total Stock in Case', 'Total stock in case'])
                    channel_col = get_col_exact(alerts_df, ['MT', 'mt', 'Channel', 'channel'])

                    # Target column AK duplicate renaming
                    if 'Local Category_2' in alerts_df.columns:
                        category_col = 'Local Category_2'
                    else:
                        local_matches = [c for c in alerts_df.columns if c.startswith('Local Category')]
                        category_col = local_matches[1] if len(local_matches) > 1 else None

                    if cr_col:
                        alerts_df[cr_col] = pd.to_numeric(alerts_df[cr_col], errors='coerce')
                    if stock_col:
                        alerts_df[stock_col] = pd.to_numeric(alerts_df[stock_col], errors='coerce')

                    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
                    with col_f1:
                        if depot_col:
                            depot_vals = sorted(set(str(x) for x in alerts_df[depot_col].dropna().unique()))
                            selected_depot = st.multiselect("Depot", depot_vals, default=[], key="alert_depot")
                        else:
                            selected_depot = []
                    with col_f2:
                        if brand_col:
                            brand_vals = sorted(set(str(x) for x in alerts_df[brand_col].dropna().unique()))
                            selected_brand = st.multiselect("Brand (IOP)", brand_vals, default=[], key="alert_brand")
                        else:
                            selected_brand = []
                    with col_f3:
                        if channel_col:
                            channel_vals = get_channel_filter_options(alerts_df, channel_col)
                            selected_channel = st.multiselect("Channel", channel_vals, default=[], key="alert_channel")
                        else:
                            selected_channel = []
                    with col_f4:
                        risk_options = ['High (20-50%)', 'Medium (50-75%)']
                        selected_risk = st.multiselect("Risk Level", risk_options, default=risk_options, key="alert_risk")
                    with col_f5:
                        if category_col:
                            cat_vals = sorted(set(str(x) for x in alerts_df[category_col].dropna().unique()))
                            selected_cat = st.multiselect("Category", cat_vals, default=[], key="alert_cat_fixed_ak")
                        else:
                            selected_cat = []

                    if selected_depot:
                        alerts_df = alerts_df[alerts_df[depot_col].astype(str).isin(selected_depot)]
                    if selected_brand:
                        alerts_df = alerts_df[alerts_df[brand_col].astype(str).isin(selected_brand)]
                    if selected_channel and channel_col:
                        alerts_df = alerts_df[alerts_df[channel_col].astype(str).isin(selected_channel)]
                    if selected_cat:
                        alerts_df = alerts_df[alerts_df[category_col].astype(str).isin(selected_cat)]

                    bucket_risk_map = {
                        '20 TO 30': 'High', '30 TO 40': 'High', '40 TO 50': 'High',
                        '50 TO 60': 'Medium', '60 TO 70': 'Medium', '70 TO 75': 'Medium'
                    }
                    if bucket_col:
                        alerts_df['Risk_Level'] = alerts_df[bucket_col].map(bucket_risk_map)
                        alerts_df = alerts_df[alerts_df['Risk_Level'].notna()]
                        if selected_risk:
                            alerts_df = alerts_df[alerts_df['Risk_Level'].isin([r.split(' ')[0] for r in selected_risk])]
                    else:
                        st.warning("Column 'Bucket %' not found. Cannot compute risk.")
                        alerts_df = pd.DataFrame() 

                    if not alerts_df.empty and (material_col or sku_desc_col):
                        primary_group_col = sku_desc_col if sku_desc_col else material_col
                        desc_cols = [brand_col, category_col, channel_col, bucket_col]
                        desc_cols = [c for c in desc_cols if c is not None and c in alerts_df.columns]
                        
                        agg_spec = {}
                        if cr_col and cr_col in alerts_df.columns: agg_spec[cr_col] = 'sum'
                        if stock_col and stock_col in alerts_df.columns: agg_spec[stock_col] = 'sum'
                        if bucket_col and bucket_col in alerts_df.columns: agg_spec[bucket_col] = lambda x: ', '.join(sorted(x.unique()))
                        agg_spec['Risk_Level'] = lambda x: 'High' if 'High' in x.unique() else 'Medium'
                        
                        for col in desc_cols:
                            if col != primary_group_col and col in alerts_df.columns:
                                agg_spec[col] = 'first'

                        grouped = alerts_df.groupby(primary_group_col).agg(agg_spec).reset_index()

                        rename_map = {}
                        if cr_col: rename_map[cr_col] = 'Value (Cr)'
                        if stock_col: rename_map[stock_col] = 'Total Stock'
                        if bucket_col: rename_map[bucket_col] = 'Bucket(s)'
                        grouped.rename(columns=rename_map, inplace=True)
                        if 'Risk_Level' not in grouped.columns:
                            grouped['Risk_Level'] = grouped['Bucket(s)'].apply(
                                lambda x: 'High' if any(b in x for b in ['20 TO 30','30 TO 40','40 TO 50']) else 'Medium'
                            )
                        
                        def simplify_buckets(bucket_str):
                            if pd.isna(bucket_str): return ""
                            parts = bucket_str.split(', ')
                            lower_bounds = []; upper_bounds = []
                            for b in parts:
                                match = re.search(r'(\d+)\s*TO\s*(\d+)', b)
                                if match:
                                    lower_bounds.append(int(match.group(1)))
                                    upper_bounds.append(int(match.group(2)))
                            if lower_bounds and upper_bounds: return f"{min(lower_bounds)}-{max(upper_bounds)}%"
                            return bucket_str

                        grouped['Shelf Life'] = grouped['Bucket(s)'].apply(simplify_buckets)

                        def est_days(bucket_str):
                            if pd.isna(bucket_str): return None
                            first = bucket_str.split(',')[0].strip()
                            if 'TO' in first:
                                parts = first.split(' TO ')
                                try:
                                    low = int(parts[0])
                                    return int(low * 3.65)
                                except: return None
                            return None
                        grouped['Est. Days Left'] = grouped['Bucket(s)'].apply(est_days)

                        def suggest_action(row):
                            risk = row['Risk_Level']; stock = row.get('Total Stock', 0)
                            if risk == 'High':
                                if stock > 100: return "Initiate promotional activities or discount to accelerate movement."
                                else: return "Coordinate with supply chain for possible return or redistribution."
                            elif risk == 'Medium':
                                if stock > 200: return "Monitor closely and consider promotional interventions if stock remains high."
                                else: return "Continue regular review; no immediate action required."
                            return "-"
                        grouped['Recommended Action'] = grouped.apply(suggest_action, axis=1)

                        # Sort whole table descending based on Value (Cr)
                        if 'Value (Cr)' in grouped.columns:
                            grouped = grouped.sort_values(by='Value (Cr)', ascending=False)
                        else:
                            grouped = grouped.sort_values('Est. Days Left', ascending=True)

                        total_high = alerts_df[alerts_df['Risk_Level'] == 'High'][cr_col].sum() if cr_col else 0
                        total_medium = alerts_df[alerts_df['Risk_Level'] == 'Medium'][cr_col].sum() if cr_col else 0
                        high_skus = grouped[grouped['Risk_Level']=='High'].shape[0]; medium_skus = grouped[grouped['Risk_Level']=='Medium'].shape[0]

                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("High Risk Value", f"{total_high:,.2f} Cr")
                        col2.metric("Medium Risk Value", f"{total_medium:,.2f} Cr")
                        col3.metric("High Risk SKUs", high_skus)
                        col4.metric("Medium Risk SKUs", medium_skus)
                        st.markdown("---")

                        if not grouped.empty:
                            display_cols = []
                            if primary_group_col and primary_group_col in grouped.columns: display_cols.append(primary_group_col)
                            if brand_col and brand_col in grouped.columns and brand_col != primary_group_col: display_cols.append(brand_col)
                            display_cols.append('Shelf Life')
                            if 'Est. Days Left' in grouped.columns: display_cols.append('Est. Days Left')
                            if 'Total Stock' in grouped.columns: display_cols.append('Total Stock')
                            if 'Value (Cr)' in grouped.columns: display_cols.append('Value (Cr)')
                            display_cols.append('Risk_Level')
                            display_cols.append('Recommended Action')

                            final_cols = [c for c in display_cols if c in grouped.columns]
                            df_display = grouped[final_cols].copy()
                            rename_display = {
                                primary_group_col: 'SKU Description',
                                brand_col: 'Brand',
                                'Shelf Life': 'Shelf Life Left', 'Est. Days Left': 'Est. Days',
                                'Total Stock': 'Stock (Cases)', 'Value (Cr)': 'Value (Cr)',
                                'Risk_Level': 'Risk', 'Recommended Action': 'Action'
                            }
                            df_display.rename(columns=rename_display, inplace=True)

                            # Re-verify descending sort order by Value (Cr)
                            if 'Value (Cr)' in df_display.columns:
                                df_display = df_display.sort_values(by='Value (Cr)', ascending=False)

                            render_styled_table(df_display, max_height=450)

                            csv = df_display.to_csv(index=False).encode('utf-8')
                            st.download_button("Download Alerts CSV", data=csv, file_name="shelf_life_alerts.csv", mime="text/csv", help="Download the alert list for offline action")
                        else: st.info("No alerts found matching the current filters.")
                    else: st.info("No alerts found. Either no data in the risk buckets or missing SKU/material column.")


        # ---- 5TH TAB: 4-WEEK COMPARISON TAB LOGIC ----
        elif tab_name == "Comparison":
            with tab:
                st.subheader("4-Week Inventory Risk and Aging Comparison")

                if stock_df is None:
                    st.warning("No stock data available. Please upload an .xlsb file with inventory data.")
                else:
                    comp_df = stock_df.copy()

                    c_week_col = get_col_exact(comp_df, ['Week', 'week', 'WEEK', 'Wk', 'wk', 'Workweek', 'WW'])
                    c_branch_col = get_col_exact(comp_df, ['Branch', 'branch', 'BRANCH', 'Region', 'region'])
                    c_mt_col = get_col_exact(comp_df, ['MT', 'mt', 'Channel', 'channel', 'CHANNEL', 'Chn'])
                    c_bucket_col = get_col_exact(comp_df, ['Bucket %', 'bucket %', 'BUCKET %', 'Bucket', 'Bucket%'])
                    c_brand_col = get_col_exact(comp_df, ['IOP', 'Brand', 'Material Description', 'brand', 'BRAND', 'Iop Category'])
                    
                    local_cat_cols = [c for c in comp_df.columns if c.startswith('Local Category')]
                    if len(local_cat_cols) > 1:
                        c_cat_col = local_cat_cols[1]
                    else:
                        c_cat_col = get_col_exact(comp_df, ['Local Category', 'Category', 'category', 'CATEGORY', 'Local Cat'])
                    
                    c_link_col = get_col_exact(comp_df, ['link des', 'link_des', 'Link des', 'SKU Des', 'SKU Description', 'SKU'])
                    c_material_col = get_col_exact(comp_df, ['Material Code', 'Material code', 'MATERIAL CODE', 'Material'])
                    c_depot_col = get_col_exact(comp_df, ['Depot Code', 'Depot code', 'DEPOT CODE', 'Depot', 'depot'])
                    c_cr_col = get_col_exact(comp_df, ['Cr', 'CR', 'cr', 'Value', 'Amount'])
                    c_stock_col = get_col_exact(comp_df, ['Total Stock in Case', 'Total stock in case', 'Stock (Cases)', 'Stock'])

                    if c_cr_col:
                        comp_df[c_cr_col] = pd.to_numeric(comp_df[c_cr_col], errors='coerce').fillna(0)
                    if c_stock_col:
                        comp_df[c_stock_col] = pd.to_numeric(comp_df[c_stock_col], errors='coerce').fillna(0)

                    # Extract sorted unique weeks
                    # Extract sorted unique weeks
                    if c_week_col and comp_df[c_week_col].notna().any():
                        raw_weeks = [str(w).strip() for w in comp_df[c_week_col].dropna().unique() if str(w).strip() != '']
                        def parse_week_val(w):
                            nums = re.findall(r'\d+', str(w))
                            return int(nums[0]) if nums else str(w)
                        try:
                            sorted_weeks = sorted(raw_weeks, key=parse_week_val)
                        except Exception:
                            sorted_weeks = sorted(raw_weeks)
                    else:
                        sorted_weeks = []

                    # Slicers & Filters (Dropdown multiselect style matching other slicers)
                    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                    with col_f1:
                        selected_weeks = st.multiselect("Week", sorted_weeks, default=[], key="comp_week_sel")
                    with col_f2:
                        branch_vals = sorted(set(str(x) for x in comp_df[c_branch_col].dropna().unique())) if c_branch_col else []
                        allowed_branches = ['01.North', '02.East', '03.West', '04.South', 'North', 'East', 'West', 'South', 'Factory']
                        branch_display = [v for v in branch_vals if any(b.lower() in v.lower() for b in allowed_branches)] or branch_vals
                        selected_branches = st.multiselect("Branch", branch_display, default=[], key="comp_branch_sel")
                    with col_f3:
                        channel_vals = get_channel_filter_options(comp_df, c_mt_col) if c_mt_col else []
                        selected_channels = st.multiselect("Channel", channel_vals, default=[], key="comp_channel_sel")
                    with col_f4:
                        cat_vals = sorted(set(str(x) for x in comp_df[c_cat_col].dropna().unique())) if c_cat_col else []
                        selected_cats = st.multiselect("Category", cat_vals, default=[], key="comp_cat_sel")

                    # Filtering DataFrame
                    filtered_comp = comp_df.copy()
                    if c_week_col and selected_weeks:
                        filtered_comp = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(selected_weeks)]
                    if c_branch_col and selected_branches:
                        filtered_comp = filtered_comp[filtered_comp[c_branch_col].astype(str).str.strip().isin(selected_branches)]
                    if c_mt_col and selected_channels:
                        filtered_comp = filtered_comp[filtered_comp[c_mt_col].astype(str).str.strip().isin(selected_channels)]
                    if c_cat_col and selected_cats:
                        filtered_comp = filtered_comp[filtered_comp[c_cat_col].astype(str).str.strip().isin(selected_cats)]

                    # Bucket classification for risk metrics
                    if c_bucket_col:
                        bucket_lower_map = {b: get_bucket_lower(b) for b in filtered_comp[c_bucket_col].dropna().unique()}
                        filtered_comp['Bucket_Lower'] = filtered_comp[c_bucket_col].map(bucket_lower_map)
                        filtered_comp['Risk_Tier'] = filtered_comp['Bucket_Lower'].apply(
                            lambda x: 'High (20-50%)' if pd.notna(x) and 20 <= x < 50 else (
                                'Medium (50-75%)' if pd.notna(x) and 50 <= x < 75 else (
                                    'Low (75-85%)' if pd.notna(x) and 75 <= x <= 85 else 'Other'
                                )
                            )
                        )
                    else:
                        filtered_comp['Risk_Tier'] = 'Unknown'

                    # Ensure we have active comparison weeks (defaults automatically to last 4 weeks if not explicitly filtered)
                    if selected_weeks:
                        active_weeks = [w for w in sorted_weeks if w in selected_weeks]
                    else:
                        active_weeks = sorted_weeks[-4:] if len(sorted_weeks) >= 4 else sorted_weeks

                    # ---- 4-WEEK KPI SUMMARY CARDS ----
                    st.markdown("### 4-Week Executive Overview")
                    if active_weeks and c_week_col and c_cr_col:
                        kpi_cols = st.columns(min(len(active_weeks), 4) if len(active_weeks) > 0 else 1)
                        weekly_totals = {}
                        weekly_high = {}
                        weekly_skus = {}

                        for idx, wk in enumerate(active_weeks[:4]):
                            wk_df = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(wk)]
                            high_cr = wk_df[wk_df['Risk_Tier'] == 'High (20-50%)'][c_cr_col].sum() if c_cr_col else 0
                            weekly_high[wk] = high_cr

                            # WoW delta calculation for High Risk Value
                            if idx > 0:
                                prev_wk = active_weeks[idx - 1]
                                prev_high = weekly_high.get(prev_wk, 0)
                                delta_high = high_cr - prev_high
                                delta_pct = (delta_high / prev_high * 100) if prev_high > 0 else 0
                                delta_str = f"{delta_high:+.2f} Cr ({delta_pct:+.1f}% WoW)"
                            else:
                                delta_str = "Baseline Week"

                            wk_display = str(wk) if str(wk).lower().startswith('week') else f"Week {wk}"

                            with kpi_cols[idx]:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #FFFFFF, #FAF5FF); padding: 16px; border-radius: 12px; border: 1.5px solid #D8B4FE; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.08); text-align: center;">
                                    <div style="color: #6B21A8; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">{wk_display} High Risk</div>
                                    <div style="color: #2E1065; font-size: 28px; font-weight: 900; margin: 6px 0;">₹{high_cr:,.2f} Cr</div>
                                    <div style="color: {'#dc2626' if 'Cr (' in delta_str and '+' in delta_str else ('#059669' if '-' in delta_str else '#6B21A8')}; font-size: 12px; font-weight: 600;">{delta_str}</div>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("Week or Value column not detected for KPI cards.")

                    st.markdown("---")

                    # ---- 4-WEEK VISUALIZATIONS ----
                    st.markdown("### 4-Weekly Risk Visualizations")
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        if c_week_col and c_cat_col and c_cr_col:
                            cat_week_df = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks[:4])].groupby([c_cat_col, c_week_col])[c_cr_col].sum().reset_index()
                            if not cat_week_df.empty:
                                fig_cat = px.bar(
                                    cat_week_df, 
                                    x=c_cat_col, 
                                    y=c_cr_col, 
                                    color=c_week_col, 
                                    barmode='group',
                                    title="Category-wise Risk Evolution across 4 Weeks (Cr)",
                                    color_discrete_sequence=['#7C3AED', '#A855F7', '#C084FC', '#E879F9', '#3B82F6'],
                                    labels={c_cr_col: 'At-Risk Value (Cr)', c_cat_col: 'Category', c_week_col: 'Week'}
                                )
                                apply_dark_theme(fig_cat, height=360)
                                st.plotly_chart(fig_cat, use_container_width=True)
                            else:
                                st.info("No data for Category 4-week chart.")
                        else:
                            st.info("Missing Category or Value columns for chart.")

                    with chart_col2:
                        if c_week_col and c_bucket_col and c_cr_col:
                            def is_comp_bucket(b):
                                if pd.isna(b): return False
                                b_clean = str(b).strip().lower().replace(' ', '')
                                return b_clean in ['30to40', '40to50', '50to60', '60to70', '70to75', '75to80', '80to85']

                            bucket_sub = filtered_comp[
                                filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks[:4]) &
                                filtered_comp[c_bucket_col].apply(is_comp_bucket)
                            ]
                            bucket_week_df = bucket_sub.groupby([c_week_col, c_bucket_col])[c_cr_col].sum().reset_index()
                            if not bucket_week_df.empty:
                                bucket_week_df['SortKey'] = bucket_week_df[c_bucket_col].apply(lambda x: get_bucket_lower(x) or 999)
                                bucket_week_df = bucket_week_df.sort_values(by=['SortKey', c_week_col]).drop(columns=['SortKey'])

                                fig_bucket = px.bar(
                                    bucket_week_df,
                                    x=c_week_col,
                                    y=c_cr_col,
                                    color=c_bucket_col,
                                    barmode='stack',
                                    title="4-Week Shelf-Life Risk Distribution Migration (Cr)",
                                    color_discrete_sequence=['#EF4444', '#F97316', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899'],
                                    labels={c_cr_col: 'At-Risk Value (Cr)', c_week_col: 'Week', c_bucket_col: 'Bucket %'}
                                )
                                apply_dark_theme(fig_bucket, height=360)
                                st.plotly_chart(fig_bucket, use_container_width=True)
                            else:
                                st.info("No data for Shelf-Life Migration chart.")
                        else:
                            st.info("Missing Bucket or Value columns for chart.")

                    # Additional Regional Comparison & SKU Surge Charts
                    chart_col3, chart_col4 = st.columns(2)
                    with chart_col3:
                        if c_week_col and c_branch_col and c_cr_col:
                            allowed_4_branches = ['01.North', '02.East', '03.West', '04.South', '1.North', '2.East', '3.West', '4.South', 'North', 'East', 'West', 'South']
                            branch_sub = filtered_comp[
                                filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks[:4]) &
                                filtered_comp[c_branch_col].astype(str).str.strip().isin(allowed_4_branches)
                            ]
                            branch_week_df = branch_sub.groupby([c_branch_col, c_week_col])[c_cr_col].sum().reset_index()
                            if not branch_week_df.empty:
                                fig_branch = px.bar(
                                    branch_week_df,
                                    x=c_branch_col,
                                    y=c_cr_col,
                                    color=c_week_col,
                                    barmode='group',
                                    title="Regional Branch Risk Comparison across 4 Weeks (Cr)",
                                    color_discrete_sequence=['#7C3AED', '#A855F7', '#C084FC', '#E879F9', '#3B82F6'],
                                    labels={c_cr_col: 'At-Risk Value (Cr)', c_branch_col: 'Branch', c_week_col: 'Week'}
                                )
                                apply_dark_theme(fig_branch, height=360)
                                st.plotly_chart(fig_branch, use_container_width=True)
                            else:
                                st.info("No data for 4 regional branches.")
                        else:
                            st.info("Branch data not available for 4-week chart.")

                    with chart_col4:
                        if c_link_col and c_week_col and c_cr_col and len(active_weeks) >= 2:
                            w_first = active_weeks[0]
                            w_last = active_weeks[-1]
                            sku_first = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_first)].groupby(c_link_col)[c_cr_col].sum()
                            sku_last = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_last)].groupby(c_link_col)[c_cr_col].sum()

                            sku_delta_df = pd.DataFrame({
                                'First': sku_first,
                                'Last': sku_last
                            }).fillna(0)
                            sku_delta_df['Net_Surge_Cr'] = sku_delta_df['Last'] - sku_delta_df['First']
                            top_surge_df = sku_delta_df.sort_values(by='Net_Surge_Cr', ascending=False).head(10).reset_index()

                            # Removed the Top 10 SKUs with Largest Risk Surge chart
                            # This block is now completely removed as requested
                        else:
                            st.info("Requires at least 2 distinct weeks to compute SKU risk surge chart.")

                    st.markdown("---")

                    # ---- DETAILED 4-WEEK COMPARISON TABLES ----
                    st.markdown("### 4-Week Comparison & Variance Matrices")

                    tab_t1, tab_t2, tab_t3 = st.tabs(["Category x 4-Week Matrix", "Shelf-Life Bucket x 4-Week Matrix", "Top 10 Escalating SKUs"])

                    with tab_t1:
                        if c_cat_col and c_week_col and c_cr_col:
                            cat_pivot = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks[:4])].pivot_table(
                                index=c_cat_col,
                                columns=c_week_col,
                                values=c_cr_col,
                                aggfunc='sum',
                                fill_value=0
                            )
                            avail_weeks = [w for w in active_weeks[:4] if w in cat_pivot.columns]
                            cat_pivot = cat_pivot.reindex(columns=avail_weeks)
                            
                            if len(avail_weeks) >= 2:
                                cat_pivot['Net 4-Wk Change (Cr)'] = cat_pivot[avail_weeks[-1]] - cat_pivot[avail_weeks[0]]
                                cat_pivot['Growth %'] = ((cat_pivot['Net 4-Wk Change (Cr)'] / cat_pivot[avail_weeks[0]].replace(0, np.nan)) * 100).fillna(0).round(1).astype(str) + '%'
                            
                            cat_pivot = cat_pivot.sort_values(by=avail_weeks[-1] if avail_weeks else cat_pivot.columns[0], ascending=False)
                            
                            total_row = cat_pivot[avail_weeks].sum().to_frame().T
                            total_row.index = ['Total']
                            if len(avail_weeks) >= 2:
                                net_tot = total_row[avail_weeks[-1]].values[0] - total_row[avail_weeks[0]].values[0]
                                total_row['Net 4-Wk Change (Cr)'] = net_tot
                                total_row['Growth %'] = f"{(net_tot / total_row[avail_weeks[0]].values[0] * 100):.1f}%" if total_row[avail_weeks[0]].values[0] > 0 else "0.0%"
                            
                            final_cat_matrix = pd.concat([cat_pivot, total_row]).reset_index().rename(columns={'index': 'Category'})
                            render_styled_table(final_cat_matrix)
                        else:
                            st.info("Columns missing for Category comparison matrix.")

                    with tab_t2:
                        if c_bucket_col and c_week_col and c_cr_col:
                            def is_comp_bucket(b):
                                if pd.isna(b): return False
                                b_clean = str(b).strip().lower().replace(' ', '')
                                return b_clean in ['30to40', '40to50', '50to60', '60to70', '70to75', '75to80', '80to85']

                            bucket_sub_matrix = filtered_comp[
                                filtered_comp[c_week_col].astype(str).str.strip().isin(active_weeks[:4]) &
                                filtered_comp[c_bucket_col].apply(is_comp_bucket)
                            ]
                            bucket_pivot = bucket_sub_matrix.pivot_table(
                                index=c_bucket_col,
                                columns=c_week_col,
                                values=c_cr_col,
                                aggfunc='sum',
                                fill_value=0
                            )
                            avail_weeks = [w for w in active_weeks[:4] if w in bucket_pivot.columns]
                            bucket_pivot = bucket_pivot.reindex(columns=avail_weeks)
                            if len(avail_weeks) >= 2:
                                bucket_pivot['Net Change (Cr)'] = bucket_pivot[avail_weeks[-1]] - bucket_pivot[avail_weeks[0]]
                            
                            bucket_pivot['SortKey'] = [get_bucket_lower(b) or 999 for b in bucket_pivot.index]
                            bucket_pivot = bucket_pivot.sort_values('SortKey').drop('SortKey', axis=1)
                            
                            total_bucket = bucket_pivot[avail_weeks].sum().to_frame().T
                            total_bucket.index = ['Total']
                            if len(avail_weeks) >= 2:
                                total_bucket['Net Change (Cr)'] = total_bucket[avail_weeks[-1]].values[0] - total_bucket[avail_weeks[0]].values[0]
                            
                            final_bucket_matrix = pd.concat([bucket_pivot, total_bucket]).reset_index().rename(columns={'index': 'Bucket %'})
                            render_styled_table(final_bucket_matrix)
                        else:
                            st.info("Columns missing for Bucket comparison matrix.")

                    with tab_t3:
                        if c_link_col and c_week_col and c_cr_col and len(active_weeks) >= 2:
                            w_first = active_weeks[0]
                            w_last = active_weeks[-1]
                            sku_first = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_first)].groupby(c_link_col)[c_cr_col].sum()
                            sku_last = filtered_comp[filtered_comp[c_week_col].astype(str).str.strip() == str(w_last)].groupby(c_link_col)[c_cr_col].sum()

                            sku_escalation = pd.DataFrame({
                                f'{w_first} (Cr)': sku_first,
                                f'{w_last} (Cr)': sku_last
                            }).fillna(0)

                            sku_escalation['Net Surge (Cr)'] = sku_escalation[f'{w_last} (Cr)'] - sku_escalation[f'{w_first} (Cr)']
                            sku_escalation['Surge %'] = ((sku_escalation['Net Surge (Cr)'] / sku_escalation[f'{w_first} (Cr)'].replace(0, np.nan)) * 100).fillna(100).round(1).astype(str) + '%'
                            sku_escalation = sku_escalation.sort_values(by='Net Surge (Cr)', ascending=False).head(10).reset_index().rename(columns={'index': 'SKU Description'})
                            sku_escalation.insert(0, '#', [str(i) for i in range(1, len(sku_escalation)+1)])
                            
                            render_styled_table(sku_escalation)
                        else:
                            st.info("Requires at least 2 distinct weeks and SKU Description column to compute escalating items.")

        # ---- 6TH TAB: BRAND & CATEGORY TREND ANALYSIS TAB LOGIC ----
        elif tab_name == "Trend Analysis":
            with tab:
                st.subheader("Brand and Product Category Trend Analysis")

                if stock_df is None:
                    st.warning("No stock data available. Please upload an .xlsb file with inventory data.")
                else:
                    trend_df = stock_df.copy()

                    t_week_col = get_col_exact(trend_df, ['Week', 'week', 'WEEK', 'Wk', 'wk', 'Workweek', 'WW'])
                    t_branch_col = get_col_exact(trend_df, ['Branch', 'branch', 'BRANCH', 'Region', 'region'])
                    t_mt_col = get_col_exact(trend_df, ['MT', 'mt', 'Channel', 'channel', 'CHANNEL', 'Chn'])
                    t_bucket_col = get_col_exact(trend_df, ['Bucket %', 'bucket %', 'BUCKET %', 'Bucket', 'Bucket%'])
                    t_brand_col = get_col_exact(trend_df, ['IOP', 'Brand', 'Material Description', 'brand', 'BRAND', 'Iop Category'])
                    
                    local_cat_cols = [c for c in trend_df.columns if c.startswith('Local Category')]
                    if len(local_cat_cols) > 1:
                        t_cat_col = local_cat_cols[1]
                    else:
                        t_cat_col = get_col_exact(trend_df, ['Local Category', 'Category', 'category', 'CATEGORY', 'Local Cat'])
                    
                    t_link_col = get_col_exact(trend_df, ['link des', 'link_des', 'Link des', 'SKU Des', 'SKU Description', 'SKU'])
                    t_material_col = get_col_exact(trend_df, ['Material Code', 'Material code', 'MATERIAL CODE', 'Material'])
                    t_depot_col = get_col_exact(trend_df, ['Depot Code', 'Depot code', 'DEPOT CODE', 'Depot', 'depot'])
                    t_cr_col = get_col_exact(trend_df, ['Cr', 'CR', 'cr', 'Value', 'Amount'])
                    t_stock_col = get_col_exact(trend_df, ['Total Stock in Case', 'Total stock in case', 'Stock (Cases)', 'Stock'])

                    if t_cr_col:
                        trend_df[t_cr_col] = pd.to_numeric(trend_df[t_cr_col], errors='coerce').fillna(0)
                    if t_stock_col:
                        trend_df[t_stock_col] = pd.to_numeric(trend_df[t_stock_col], errors='coerce').fillna(0)

                    # Bucket classification for risk metrics
                    if t_bucket_col:
                        bucket_lower_map = {b: get_bucket_lower(b) for b in trend_df[t_bucket_col].dropna().unique()}
                        trend_df['Bucket_Lower'] = trend_df[t_bucket_col].map(bucket_lower_map)
                        trend_df['Is_High_Risk'] = trend_df['Bucket_Lower'].apply(lambda x: 1 if pd.notna(x) and 20 <= x < 50 else 0)
                        trend_df['Is_Safe_Stock'] = trend_df['Bucket_Lower'].apply(lambda x: 1 if pd.notna(x) and x >= 70 else 0)
                    else:
                        trend_df['Is_High_Risk'] = 0
                        trend_df['Is_Safe_Stock'] = 1

                    if t_cr_col:
                        trend_df['High_Risk_Cr'] = np.where(trend_df['Is_High_Risk'] == 1, trend_df[t_cr_col], 0.0)
                    else:
                        trend_df['High_Risk_Cr'] = 0.0

                    # Available dimensions
                    dim_options = {}
                    if t_cat_col: dim_options["Category"] = t_cat_col
                    if t_brand_col: dim_options["Brand (IOP)"] = t_brand_col
                    if t_link_col: dim_options["Product / SKU"] = t_link_col
                    if t_branch_col: dim_options["Branch"] = t_branch_col

                    # Controls bar
                    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                    with col_c1:
                        chosen_dim_label = st.selectbox("Primary Dimension", list(dim_options.keys()) if dim_options else ["Category"], key="trend_dim")
                        chosen_dim_col = dim_options.get(chosen_dim_label, t_cat_col)
                    with col_c2:
                        chosen_metric = st.selectbox("Trend Metric", ["At-Risk Value (Cr)", "Total Stock (Cases)", "% Critical Risk (<50% life)"], key="trend_metric")
                    with col_c3:
                        top_n = st.selectbox("Show Top N Items", [5, 10, 15, "All"], index=1, key="trend_top_n")
                    with col_c4:
                        branch_vals = sorted(set(str(x) for x in trend_df[t_branch_col].dropna().unique())) if t_branch_col else []
                        allowed_branches = ['01.North', '02.East', '03.West', '04.South', 'North', 'East', 'West', 'South', 'Factory']
                        branch_display = [v for v in branch_vals if any(b.lower() in v.lower() for b in allowed_branches)] or branch_vals
                        selected_branches_tr = st.multiselect("Filter Branch", branch_display, default=[], key="trend_branch_filter")

                    # Filters
                    filtered_tr = trend_df.copy()
                    if t_branch_col and selected_branches_tr:
                        filtered_tr = filtered_tr[filtered_tr[t_branch_col].astype(str).str.strip().isin(selected_branches_tr)]

                    # ---- SUPPLY CHAIN STRATEGIC KPIS ----
                    st.markdown("### Supply Chain Trend Intelligence KPIs")
                    kpi_tr1, kpi_tr2, kpi_tr3, kpi_tr4 = st.columns(4)

                    total_val_all = filtered_tr[t_cr_col].sum() if t_cr_col else 0
                    total_stock_all = filtered_tr[t_stock_col].sum() if t_stock_col else 0
                    
                    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
                        dim_totals = filtered_tr.groupby(chosen_dim_col)[t_cr_col].sum().sort_values(ascending=False)
                        top_contributor = dim_totals.index[0] if not dim_totals.empty else "N/A"
                        top_contributor_val = dim_totals.iloc[0] if not dim_totals.empty else 0
                        top_contributor_pct = (top_contributor_val / total_val_all * 100) if total_val_all > 0 else 0
                        
                        cum_share = dim_totals.cumsum() / total_val_all
                        pareto_count = len(cum_share[cum_share <= 0.80]) + 1
                        pareto_pct = (pareto_count / len(dim_totals) * 100) if len(dim_totals) > 0 else 0
                    else:
                        top_contributor = "N/A"
                        top_contributor_val = 0
                        top_contributor_pct = 0
                        pareto_count = 0
                        pareto_pct = 0

                    if t_cr_col and not filtered_tr.empty:
                        safe_val = filtered_tr[filtered_tr['Is_Safe_Stock'] == 1][t_cr_col].sum()
                        freshness_ratio = (safe_val / total_val_all * 100) if total_val_all > 0 else 100
                        high_risk_val = filtered_tr[filtered_tr['Is_High_Risk'] == 1][t_cr_col].sum()
                        high_risk_pct = (high_risk_val / total_val_all * 100) if total_val_all > 0 else 0
                    else:
                        freshness_ratio = 100
                        high_risk_pct = 0

                    with kpi_tr1:
                        st.metric("Top Risk Contributor", f"₹{top_contributor_val:,.2f} Cr", delta=f"{top_contributor_pct:.1f}% Share ({str(top_contributor)[:15]})", delta_color="inverse")
                    with kpi_tr2:
                        st.metric("Pareto 80/20 Concentration", f"{pareto_count} {chosen_dim_label}s", delta=f"Drives 80% exposure ({pareto_pct:.0f}% of items)")
                    with kpi_tr3:
                        st.metric("Critical Risk Rate (<50%)", f"{high_risk_pct:.1f}%", delta=f"₹{high_risk_val:,.2f} Cr at critical risk", delta_color="inverse")
                    with kpi_tr4:
                        st.metric("Freshness Health Index", f"{freshness_ratio:.1f}%", delta="Stock >70% shelf life")

                    st.markdown("---")

                    # ---- DATA SCIENCE VISUALIZATIONS ----
                    st.markdown("### Multi-Dimensional Visualizations")

                    vis_col1, vis_col2 = st.columns(2)

                    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
                        item_ranks = filtered_tr.groupby(chosen_dim_col)[t_cr_col].sum().sort_values(ascending=False)
                        if top_n != "All":
                            target_items = item_ranks.head(int(top_n)).index.tolist()
                        else:
                            target_items = item_ranks.index.tolist()
                        plot_df = filtered_tr[filtered_tr[chosen_dim_col].isin(target_items)]
                    else:
                        target_items = []
                        plot_df = filtered_tr.copy()

                    with vis_col1:
                        if t_week_col and chosen_dim_col and not plot_df.empty:
                            if chosen_metric == "At-Risk Value (Cr)":
                                trend_agg = plot_df.groupby([t_week_col, chosen_dim_col])[t_cr_col].sum().reset_index()
                                y_col = t_cr_col
                                y_label = "Value at Risk (Cr)"
                            elif chosen_metric == "Total Stock (Cases)":
                                trend_agg = plot_df.groupby([t_week_col, chosen_dim_col])[t_stock_col].sum().reset_index()
                                y_col = t_stock_col
                                y_label = "Stock (Cases)"
                            else:
                                hr_agg = plot_df.groupby([t_week_col, chosen_dim_col]).apply(
                                    lambda g: (g[g['Is_High_Risk'] == 1][t_cr_col].sum() / g[t_cr_col].sum() * 100) if g[t_cr_col].sum() > 0 else 0
                                ).reset_index(name='High_Risk_Pct')
                                trend_agg = hr_agg
                                y_col = 'High_Risk_Pct'
                                y_label = "% Critical Risk (<50% life)"

                            fig_trend = px.line(
                                trend_agg,
                                x=t_week_col,
                                y=y_col,
                                color=chosen_dim_col,
                                markers=True,
                                title=f"{chosen_dim_label} Trajectory ({chosen_metric})",
                                color_discrete_sequence=['#9B59B6', '#EC4899', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#6366F1', '#14B8A6'],
                                labels={y_col: y_label, t_week_col: 'Week', chosen_dim_col: chosen_dim_label}
                            )
                            fig_trend.update_traces(line=dict(width=3), marker=dict(size=8))
                            apply_dark_theme(fig_trend, height=380)
                            st.plotly_chart(fig_trend, use_container_width=True)
                        else:
                            st.info("Week column required for time-series trend line.")

                    with vis_col2:
                        if chosen_dim_col and t_cr_col and not filtered_tr.empty:
                            pareto_df = filtered_tr.groupby(chosen_dim_col)[t_cr_col].sum().sort_values(ascending=False).reset_index()
                            if top_n != "All":
                                pareto_df = pareto_df.head(int(top_n))
                            else:
                                pareto_df = pareto_df.head(15)

                            total_pareto_val = pareto_df[t_cr_col].sum()
                            pareto_df['Cum_Val'] = pareto_df[t_cr_col].cumsum()
                            pareto_df['Cum_Pct'] = ((pareto_df['Cum_Val'] / total_pareto_val) * 100).round(1) if total_pareto_val > 0 else 0

                            fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
                            fig_pareto.add_trace(
                                go.Bar(
                                    x=pareto_df[chosen_dim_col],
                                    y=pareto_df[t_cr_col],
                                    name="At-Risk Value (Cr)",
                                    marker_color="#7C3AED",
                                    opacity=0.85
                                ),
                                secondary_y=False,
                            )
                            fig_pareto.add_trace(
                                go.Scatter(
                                    x=pareto_df[chosen_dim_col],
                                    y=pareto_df['Cum_Pct'],
                                    name="Cumulative Exposure %",
                                    mode="lines+markers",
                                    line=dict(color="#EC4899", width=3),
                                    marker=dict(size=7, color="#EC4899")
                                ),
                                secondary_y=True,
                            )
                            fig_pareto.add_hline(
                                y=80, line_dash="dash", line_color="#EF4444", secondary_y=True,
                                annotation_text="80% Pareto Cutoff", annotation_position="top right", annotation_font_color="#EF4444"
                            )
                            fig_pareto.update_yaxes(title_text="Value at Risk (Cr)", secondary_y=False)
                            fig_pareto.update_yaxes(title_text="Cumulative Exposure %", secondary_y=True, range=[0, 105], showgrid=False)
                            fig_pareto.update_layout(
                                title=f"Pareto 80/20 Risk Exposure Distribution by {chosen_dim_label}",
                                barmode="group",
                            )
                            apply_dark_theme(fig_pareto, height=380)
                            st.plotly_chart(fig_pareto, use_container_width=True)
                        else:
                            st.info("Insufficient data for Pareto Exposure Chart.")

                    st.markdown("---")

                    # Additional Trend Visualizations
                    row2_col1, row2_col2 = st.columns(2)

                    with row2_col1:
                        if chosen_dim_col and t_bucket_col and t_cr_col and target_items:
                            if chosen_dim_col == t_bucket_col:
                                comp_chart_df = filtered_tr.groupby(t_bucket_col)[t_cr_col].sum().reset_index()
                                if not comp_chart_df.empty:
                                    fig_comp = px.bar(
                                        comp_chart_df,
                                        x=t_bucket_col,
                                        y=t_cr_col,
                                        color=t_bucket_col,
                                        title="Shelf-Life Bucket Distribution (Cr)",
                                        color_discrete_sequence=['#EF4444', '#F97316', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899'],
                                        labels={t_cr_col: 'Value (Cr)', t_bucket_col: 'Bucket'}
                                    )
                                    apply_dark_theme(fig_comp, height=360)
                                    st.plotly_chart(fig_comp, use_container_width=True)
                                else:
                                    st.info("No composition data available.")
                            else:
                                comp_chart_df = filtered_tr[filtered_tr[chosen_dim_col].isin(target_items[:8])].groupby([chosen_dim_col, t_bucket_col])[t_cr_col].sum().reset_index()
                                if not comp_chart_df.empty:
                                    fig_comp = px.bar(
                                        comp_chart_df,
                                        x=chosen_dim_col,
                                        y=t_cr_col,
                                        color=t_bucket_col,
                                        barmode='relative',
                                        title=f"Shelf-Life Health Profile for Top {chosen_dim_label}s",
                                        color_discrete_sequence=['#EF4444', '#F97316', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899'],
                                        labels={t_cr_col: 'Value (Cr)', chosen_dim_col: chosen_dim_label, t_bucket_col: 'Bucket'}
                                    )
                                    apply_dark_theme(fig_comp, height=360)
                                    st.plotly_chart(fig_comp, use_container_width=True)
                                else:
                                    st.info("No composition data available.")
                        else:
                            st.info("Missing Bucket or Dimension data.")

                    with row2_col2:
                        # Determine secondary breakdown column dynamically to prevent duplicate column in groupby
                        if chosen_dim_col == t_branch_col and t_cat_col:
                            secondary_col = t_cat_col
                            sec_label = "Category"
                        elif t_branch_col and chosen_dim_col != t_branch_col:
                            secondary_col = t_branch_col
                            sec_label = "Branch"
                        elif t_mt_col and chosen_dim_col != t_mt_col:
                            secondary_col = t_mt_col
                            sec_label = "Channel"
                        else:
                            secondary_col = None
                            sec_label = ""

                        if chosen_dim_col and secondary_col and t_cr_col and target_items:
                            branch_dist_df = filtered_tr[filtered_tr[chosen_dim_col].isin(target_items[:6])].groupby([chosen_dim_col, secondary_col])[t_cr_col].sum().reset_index()
                            if not branch_dist_df.empty:
                                fig_br_dist = px.bar(
                                    branch_dist_df,
                                    x=chosen_dim_col,
                                    y=t_cr_col,
                                    color=secondary_col,
                                    barmode='group',
                                    title=f"{sec_label} Breakdown for Top {chosen_dim_label}s (Cr)",
                                    color_discrete_sequence=['#7C3AED', '#A855F7', '#C084FC', '#E879F9', '#3B82F6', '#10B981'],
                                    labels={t_cr_col: 'Value (Cr)', chosen_dim_col: chosen_dim_label, secondary_col: sec_label}
                                )
                                apply_dark_theme(fig_br_dist, height=360)
                                st.plotly_chart(fig_br_dist, use_container_width=True)
                            else:
                                st.info(f"No {sec_label.lower()} distribution data available.")
                        else:
                            st.info("Distribution breakdown data currently unavailable.")

                    st.markdown("---")

                    # ---- TREND LEADERBOARD TABLE ----
                    st.subheader(f"{chosen_dim_label} Strategic Risk Leaderboard")
                    if chosen_dim_col and t_cr_col and not filtered_tr.empty:
                        agg_dict = {
                            t_cr_col: 'sum',
                            'High_Risk_Cr': 'sum'
                        }
                        if t_stock_col:
                            agg_dict[t_stock_col] = 'sum'

                        leaderboard = filtered_tr.groupby(chosen_dim_col).agg(agg_dict).reset_index()
                        leaderboard.rename(columns={
                            t_cr_col: 'Total Exposure (Cr)',
                            'High_Risk_Cr': 'High Risk Val (Cr)',
                            t_stock_col: 'Stock (Cases)' if t_stock_col else 'Cases'
                        }, inplace=True)
                        
                        leaderboard['High Risk %'] = ((leaderboard['High Risk Val (Cr)'] / leaderboard['Total Exposure (Cr)'].replace(0, np.nan)) * 100).fillna(0).round(1).astype(str) + '%'
                        leaderboard['Share of Total %'] = ((leaderboard['Total Exposure (Cr)'] / total_val_all) * 100).round(1).astype(str) + '%'
                        
                        def assign_strategy(row):
                            val = row['Total Exposure (Cr)']
                            hr_num = float(row['High Risk %'].replace('%', ''))
                            if hr_num >= 40 and val > 1.0:
                                return "Urgent Flash Liquidation / BOGO"
                            elif hr_num >= 40:
                                return "Targeted Channel Promotion"
                            elif val > 1.0:
                                return "Priority Fast-Track Distribution"
                            else:
                                return "Regular Supply Chain Monitoring"

                        leaderboard['Prescribed Strategy'] = leaderboard.apply(assign_strategy, axis=1)
                        leaderboard = leaderboard.sort_values(by='Total Exposure (Cr)', ascending=False).reset_index(drop=True)
                        leaderboard.insert(0, 'Rank', [f"#{i+1}" for i in range(len(leaderboard))])
                        render_styled_table(leaderboard, max_height=450)

                        csv_tr = leaderboard.to_csv(index=False).encode('utf-8')
                        st.download_button("Download Strategic Leaderboard CSV", data=csv_tr, file_name=f"{chosen_dim_label.lower()}_trend_analysis.csv", mime="text/csv")
                    else:
                        st.info("Leaderboard data currently unavailable.")

        # ---- EXISTING SHEET LOGIC (SHEET 1 & SHEET 2) ----
        else:
            with tab:
                df = sheets[tab_name].copy()

                week_col = get_col_exact(df, ['Week', 'week', 'WEEK', 'Wk'])
                branch_col = get_col_exact(df, ['Branch', 'branch', 'BRANCH'])
                mt_col = get_col_exact(df, ['MT', 'mt', 'Channel', 'channel'])
                bucket_col = get_col_exact(df, ['Bucket %', 'bucket %', 'BUCKET %'])
                material_col = get_col_exact(df, ['Material Code', 'Material code', 'MATERIAL CODE'])
                stock_col = get_col_exact(df, ['Total Stock in Case', 'Total stock in case'])
                cr_col = get_col_exact(df, ['Cr', 'CR', 'cr'])

                if stock_col: df[stock_col] = pd.to_numeric(df[stock_col], errors='coerce')
                if cr_col: df[cr_col] = pd.to_numeric(df[cr_col], errors='coerce')

                if 'Master' in tab_name or 'master' in tab_name:
                    if week_col: df[week_col] = pd.to_numeric(df[week_col], errors='coerce')
                    filter_candidates = ['Depot', 'Material code', 'Category', 'Depot Description', 'Base code Des.', 'Iop Category']
                    kpi_type = 'master'
                else:
                    filter_candidates = [c for c in [week_col, branch_col, mt_col, bucket_col] if c]
                    kpi_type = 'stock'
                    stock_df = df.copy()

                available_filters = [col for col in filter_candidates if col in df.columns]
                filters = {}
                if available_filters:
                    for i in range(0, len(available_filters), 5):
                        chunk = available_filters[i:i+5]
                        cols = st.columns(len(chunk))
                        for j, col in enumerate(chunk):
                            raw_unique_vals = sorted(set(str(x) for x in df[col].dropna().unique()))
                            
                            if col == branch_col:
                                allowed_branches = ['01.North', '02.East', '03.West', '04.South']
                                raw_unique_vals = [v for v in raw_unique_vals if v in allowed_branches]
                            elif col == mt_col:
                                raw_unique_vals = get_channel_filter_options(raw_unique_vals)
                            
                            display_options = []
                            if col == bucket_col:
                                base_buckets = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75']
                                for b in base_buckets:
                                    if b in raw_unique_vals:
                                        display_options.append(b)
                                display_options.append('>75%')
                            else:
                                display_options = raw_unique_vals
                            
                            if display_options:
                                selected = cols[j].multiselect(
                                    f"{col}", 
                                    options=display_options, 
                                    default=[], 
                                    key=f"filter_{tab_name}_{col}_{i}_{j}"
                                )
                                filters[col] = selected

                filtered_df = df.copy()
                for col, selected_vals in filters.items():
                    if selected_vals:
                        if col == bucket_col:
                            expanded_selection = []
                            for selected in selected_vals:
                                if selected == '>75%':
                                    for bucket in raw_unique_vals:
                                        if bucket in ['75 to 80', '80 to 85']:
                                            expanded_selection.append(bucket)
                                else:
                                    expanded_selection.append(selected)
                            expanded_selection = list(set(expanded_selection))
                            if expanded_selection:
                                filtered_df = filtered_df[filtered_df[col].astype(str).isin(expanded_selection)]
                        else:
                            filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_vals)]

                if kpi_type == 'master':
                    k1, k2, k3, k4 = st.columns(4)
                    with k1: st.metric("Rows", len(filtered_df))
                    with k2: st.metric("Unique Materials", filtered_df[material_col].nunique() if material_col else 0)
                    with k3: st.metric("Unique Depots", filtered_df['Depot'].nunique() if 'Depot' in filtered_df.columns else 0)
                    with k4: st.metric("Unique Categories", filtered_df['Category'].nunique() if 'Category' in filtered_df.columns else 0)

                    display_df = filtered_df.copy()
                    
                    target_base_names = [
                        'Material code', 'SKU Des', 'Link Code', 'Base Code', 'Base code Des.',
                        'Category', 'Iop Category', 'Line SKU', 'Base Code', 'Material code',
                        'Weight per CSE', 'IOP Cat', 'Total Shelf life', 'Chn'
                    ]
                    
                    selected_cols = []
                    used_cols = set()
                    
                    for base in target_base_names:
                        matched = False
                        if base in display_df.columns and base not in used_cols:
                            selected_cols.append(base)
                            used_cols.add(base)
                            matched = True
                        else:
                            for col in display_df.columns:
                                if col not in used_cols and col.startswith(base + '_'):
                                    selected_cols.append(col)
                                    used_cols.add(col)
                                    matched = True
                                    break
                    
                    if selected_cols:
                        display_df = display_df[selected_cols]

                else:
                    total_value = filtered_df[cr_col].sum() if cr_col else 0
                    k1, k2, k3, k4 = st.columns(4)
                    with k1: st.metric("Rows", len(filtered_df))
                    with k2: st.metric("Total Stock", f"{int(filtered_df[stock_col].sum()):,}" if stock_col else 0)
                    with k3: st.metric("Amount (Crores)", f"₹{total_value:,.2f} Cr")
                    with k4: st.metric("SKUs", filtered_df[material_col].nunique() if material_col else 0)

                    display_df = filtered_df.copy()

                for col in display_df.columns:
                    if not pd.api.types.is_numeric_dtype(display_df[col]):
                        display_df[col] = display_df[col].fillna('').astype(str)
                
                render_styled_table(display_df.head(200) if len(display_df) > 200 else display_df, max_height=500)
                if len(display_df) > 200:
                    st.caption(f"Displaying top 200 of {len(display_df):,} rows. Use filters above to narrow down results.")

else:
    st.info("Please upload an .xlsb file using the sidebar.")