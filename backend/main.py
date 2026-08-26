import os
import sys
import re
from typing import Dict, List, Optional, Union

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    CACHE, get_db_connection, load_file_into_cache, load_active_or_latest_from_sqlite,
    save_uploaded_file_to_history, auto_init_default_workbook
)
from parser import parse_xlsb_bytes
from analytics import (
    calculate_sheet_data, calculate_dashboard_data, calculate_alerts_data,
    calculate_comparison_data, calculate_trend_data
)

app = FastAPI(title="Inventory Aging & Risk Analytics API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_init():
    auto_init_default_workbook()

# -------------------------------------------------------------
# API ROUTE: History & Management
# -------------------------------------------------------------
@app.get("/api/files/history")
async def get_files_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, uploaded_at, stock_sheet_name, sheet_names, total_rows, is_active FROM _files_history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "filename": r["filename"],
            "uploaded_at": r["uploaded_at"],
            "stock_sheet_name": r["stock_sheet_name"],
            "sheet_names": r["sheet_names"].split(",") if r["sheet_names"] else [],
            "total_rows": r["total_rows"],
            "is_active": bool(r["is_active"])
        })
    return {"history": history, "active_file_id": CACHE.get("active_file_id")}

class SelectFileRequest(BaseModel):
    file_id: int

@app.post("/api/files/select")
async def select_active_file(req: SelectFileRequest):
    success = load_file_into_cache(req.file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found in database history")
    return {
        "status": "success",
        "file_id": req.file_id,
        "filename": CACHE.get("filename"),
        "sheets": list(CACHE.get("sheets", {}).keys()),
        "stock_sheet_name": CACHE.get("stock_sheet_name")
    }

@app.delete("/api/files/{file_id}")
async def delete_file_from_history(file_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM _files_history WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="File not found")

    sheet_names = row["sheet_names"].split(",") if row["sheet_names"] else []
    for name in sheet_names:
        clean_sheet = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
        table_name = f"f_{file_id}_{clean_sheet}"
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    cursor.execute("DELETE FROM _files_history WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()

    if CACHE.get("active_file_id") == file_id:
        CACHE["active_file_id"] = None
        CACHE["filename"] = None
        CACHE["sheets"] = {}
        CACHE["stock_sheet_name"] = None
        CACHE["loaded"] = False
        load_active_or_latest_from_sqlite()

    return {"status": "success", "message": f"Deleted file {file_id} from database"}

# -------------------------------------------------------------
# API ROUTE: Upload file
# -------------------------------------------------------------
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    if not file.filename.lower().endswith('.xlsb'):
        raise HTTPException(status_code=400, detail="Only .xlsb files are supported.")
    
    try:
        sheets = parse_xlsb_bytes(contents, file.filename)
        if not sheets:
            raise HTTPException(status_code=400, detail="No sheets found in workbook.")

        stock_sheet_name = next((s for s in sheets if 'master' not in s.lower()), list(sheets.keys())[0])

        file_id = save_uploaded_file_to_history(file.filename, sheets, stock_sheet_name)
        load_file_into_cache(file_id)

        sheet_summaries = []
        for name, df in sheets.items():
            sheet_summaries.append({
                "name": name,
                "rows": len(df),
                "columns": len(df.columns),
                "is_master": "master" in name.lower()
            })

        return {
            "status": "success",
            "file_id": file_id,
            "filename": file.filename,
            "sheets": list(sheets.keys()),
            "sheet_summaries": sheet_summaries,
            "stock_sheet_name": stock_sheet_name,
            "persisted_in_db": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")

# -------------------------------------------------------------
# API ROUTE: Sheet Metadata & Status
# -------------------------------------------------------------
@app.get("/api/sheets")
async def get_sheets():
    if not CACHE.get("loaded"):
        load_active_or_latest_from_sqlite()
        
    sheets = CACHE.get("sheets", {})
    if not sheets:
        return {"loaded": False, "filename": None, "sheets": [], "active_file_id": None}
    return {
        "loaded": True,
        "active_file_id": CACHE.get("active_file_id"),
        "filename": CACHE.get("filename"),
        "stock_sheet_name": CACHE.get("stock_sheet_name"),
        "sheets": list(sheets.keys()),
        "summaries": [
            {"name": name, "rows": len(df), "columns": len(df.columns), "is_master": "master" in name.lower()}
            for name, df in sheets.items()
        ]
    }

# -------------------------------------------------------------
# API ROUTE: Raw Sheet Data with Filters & KPIs
# -------------------------------------------------------------
class SheetDataFilterRequest(BaseModel):
    sheet_name: str
    filters: Optional[Dict[str, List[str]]] = {}
    limit: Optional[int] = 200
    offset: Optional[int] = 0

@app.post("/api/sheet-data")
async def get_sheet_data(req: SheetDataFilterRequest):
    res = calculate_sheet_data(req.sheet_name, req.filters or {}, req.limit or 200, req.offset or 0)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

# -------------------------------------------------------------
# API ROUTE: Dashboard Tab
# -------------------------------------------------------------
class DashboardFilterRequest(BaseModel):
    week: Optional[List[str]] = []
    branch: Optional[List[str]] = []
    channel: Optional[List[str]] = []

@app.post("/api/dashboard")
async def get_dashboard_data(req: DashboardFilterRequest):
    res = calculate_dashboard_data(req.week or [], req.branch or [], req.channel or [])
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

# -------------------------------------------------------------
# API ROUTE: Alert View Tab
# -------------------------------------------------------------
class AlertFilterRequest(BaseModel):
    depot: Optional[List[str]] = []
    brand: Optional[List[str]] = []
    channel: Optional[List[str]] = []
    risk: Optional[List[str]] = []
    category: Optional[List[str]] = []

@app.post("/api/alerts")
async def get_alerts_data(req: AlertFilterRequest):
    res = calculate_alerts_data(
        req.depot or [], req.brand or [], req.channel or [], req.risk or [], req.category or []
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

# -------------------------------------------------------------
# API ROUTE: Comparison Tab (Dynamic 1 to 4 Weeks Support)
# -------------------------------------------------------------
class ComparisonFilterRequest(BaseModel):
    mode: Optional[str] = "weekly"
    weeks: Optional[List[str]] = []
    branches: Optional[List[str]] = []
    channels: Optional[List[str]] = []
    categories: Optional[List[str]] = []
    brands: Optional[List[str]] = []

@app.post("/api/comparison")
async def get_comparison_data(req: ComparisonFilterRequest):
    res = calculate_comparison_data(
        req.mode or "weekly",
        req.weeks or [],
        req.branches or [],
        req.channels or [],
        req.categories or [],
        req.brands or []
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

# -------------------------------------------------------------
# API ROUTE: Trend Analysis Tab
# -------------------------------------------------------------
class TrendFilterRequest(BaseModel):
    dimension: Optional[str] = "Category"
    metric: Optional[str] = "At-Risk Value (Cr)"
    top_n: Optional[Union[int, str]] = 10
    branches: Optional[List[str]] = []

@app.post("/api/trend-analysis")
async def get_trend_data(req: TrendFilterRequest):
    res = calculate_trend_data(
        req.dimension or "Category", req.metric or "At-Risk Value (Cr)", req.top_n or 10, req.branches or []
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

if __name__ == "__main__":
    import uvicorn
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    uvicorn.run(app, host="127.0.0.1", port=8000)
