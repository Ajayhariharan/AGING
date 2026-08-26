import os
import sys
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from parser import sanitize_df, parse_xlsb_bytes

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

CACHE: Dict[str, Any] = {
    "active_file_id": None,
    "filename": None,
    "sheets": {},
    "stock_sheet_name": None,
    "loaded": False,
    "all_workbooks": {} # In-memory RAM cache for all uploaded workbooks {file_id: {filename, sheets, stock_sheet_name}}
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _files_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            stock_sheet_name TEXT,
            sheet_names TEXT,
            total_rows INTEGER,
            is_active INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_uploaded_file_to_history(filename: str, sheets: Dict[str, pd.DataFrame], stock_sheet_name: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE _files_history SET is_active = 0")
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_names_str = ",".join(sheets.keys())
    total_rows = sum(len(df) for df in sheets.values())

    cursor.execute("""
        INSERT INTO _files_history (filename, uploaded_at, stock_sheet_name, sheet_names, total_rows, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    """, (filename, now_str, stock_sheet_name, sheet_names_str, total_rows))
    file_id = cursor.lastrowid

    # Save each sheet table namespaced by file_id
    for name, df in sheets.items():
        clean_sheet = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        table_name = f"f_{file_id}_{clean_sheet}"
        df_to_save = df.copy()
        df_to_save.to_sql(table_name, conn, if_exists="replace", index=False)
        
        # Create indexes
        for col in df_to_save.columns:
            if any(k in col.lower() for k in ['week', 'branch', 'channel', 'mt', 'bucket', 'category', 'iop', 'brand', 'depot']):
                clean_idx_col = f'"{col}"'
                idx_name = f"idx_f_{file_id}_{clean_sheet}_{re.sub(r'[^a-zA-Z0-9_]', '', col)}"
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({clean_idx_col})")
                except Exception:
                    pass

    conn.commit()
    conn.close()

    # Store in fast RAM cache
    CACHE["all_workbooks"][file_id] = {
        "filename": filename,
        "sheets": sheets,
        "stock_sheet_name": stock_sheet_name
    }

    return file_id

def load_file_into_cache(file_id: int) -> bool:
    # 1. Check RAM cache first
    if file_id in CACHE["all_workbooks"]:
        wb = CACHE["all_workbooks"][file_id]
        CACHE["active_file_id"] = file_id
        CACHE["filename"] = wb["filename"]
        CACHE["sheets"] = wb["sheets"]
        CACHE["stock_sheet_name"] = wb["stock_sheet_name"]
        CACHE["loaded"] = True

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE _files_history SET is_active = 0")
        cursor.execute("UPDATE _files_history SET is_active = 1 WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()
        return True

    # 2. Otherwise load from SQLite and cache in RAM
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM _files_history WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    cursor.execute("UPDATE _files_history SET is_active = 0")
    cursor.execute("UPDATE _files_history SET is_active = 1 WHERE id = ?", (file_id,))
    conn.commit()

    filename = row["filename"]
    stock_sheet_name = row["stock_sheet_name"]
    sheet_names = row["sheet_names"].split(",") if row["sheet_names"] else []

    sheets = {}
    for name in sheet_names:
        if not name.strip():
            continue
        clean_sheet = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
        table_name = f"f_{file_id}_{clean_sheet}"
        try:
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            sheets[name.strip()] = sanitize_df(df)
        except Exception as e:
            print(f"[DB] Error loading table {table_name}: {e}")

    conn.close()

    if sheets:
        CACHE["all_workbooks"][file_id] = {
            "filename": filename,
            "sheets": sheets,
            "stock_sheet_name": stock_sheet_name
        }
        CACHE["active_file_id"] = file_id
        CACHE["filename"] = filename
        CACHE["sheets"] = sheets
        CACHE["stock_sheet_name"] = stock_sheet_name
        CACHE["loaded"] = True
        return True
    return False

def preload_all_workbooks_into_ram():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, stock_sheet_name, sheet_names FROM _files_history ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    for r in rows:
        f_id = r["id"]
        if f_id not in CACHE["all_workbooks"]:
            f_name = r["filename"]
            s_name = r["stock_sheet_name"]
            sheet_names = r["sheet_names"].split(",") if r["sheet_names"] else []
            sheets = {}
            conn_sub = get_db_connection()
            for s in sheet_names:
                if not s.strip(): continue
                clean_sheet = re.sub(r'[^a-zA-Z0-9_]', '_', s.strip())
                table_name = f"f_{f_id}_{clean_sheet}"
                try:
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn_sub)
                    sheets[s.strip()] = sanitize_df(df)
                except Exception:
                    pass
            conn_sub.close()
            if sheets:
                CACHE["all_workbooks"][f_id] = {
                    "filename": f_name,
                    "sheets": sheets,
                    "stock_sheet_name": s_name
                }

def load_active_or_latest_from_sqlite() -> bool:
    preload_all_workbooks_into_ram()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM _files_history WHERE is_active = 1 LIMIT 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM _files_history ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    conn.close()

    if row:
        return load_file_into_cache(row["id"])
    return False

def get_stock_df() -> Optional[pd.DataFrame]:
    sheets = CACHE.get("sheets", {})
    if not sheets:
        if load_active_or_latest_from_sqlite():
            sheets = CACHE.get("sheets", {})
        else:
            return None
    sname = CACHE.get("stock_sheet_name")
    if sname and sname in sheets:
        return CACHE["sheets"][sname]
    for name, df in sheets.items():
        if 'master' not in name.lower():
            return df
    return list(sheets.values())[0] if sheets else None

def auto_init_default_workbook():
    if load_active_or_latest_from_sqlite():
        return
    root_dir = os.path.dirname(os.path.dirname(__file__))
    june_path = os.path.join(root_dir, "JUNE.xlsb")
    if os.path.exists(june_path):
        try:
            print(f"[Init] Initializing database from {june_path}...")
            with open(june_path, "rb") as f:
                sheets = parse_xlsb_bytes(f.read(), "JUNE.xlsb")
            if sheets:
                stock_name = next((s for s in sheets if 'master' not in s.lower()), list(sheets.keys())[0])
                file_id = save_uploaded_file_to_history("JUNE.xlsb", sheets, stock_name)
                load_file_into_cache(file_id)
                print("[Init] Initialized DB with JUNE.xlsb in history!")
        except Exception as e:
            print(f"[Init] Could not auto-load JUNE.xlsb: {e}")
