import sys
import os
import sqlite3
import pandas as pd
import asyncio

backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_dir)
import main as app_module
import database as db
import analytics as an

async def test_july():
    # Select July file (file_id = 3)
    db.load_file_into_cache(3)
    print("Loaded active file:", db.CACHE["filename"])

    # 1. Sheets
    sheets_res = await app_module.get_sheets()
    print("Sheets Loaded:", sheets_res["loaded"], sheets_res["filename"], sheets_res["sheets"])

    # 2. Dashboard
    dash_res = await app_module.get_dashboard_data(app_module.DashboardFilterRequest())
    print("\n--- DASHBOARD ---")
    print("High Risk (Cr):", dash_res["risk_cards"]["high_risk_cr"])
    print("Med Risk (Cr):", dash_res["risk_cards"]["med_risk_cr"])
    print("Category Table Rows:", len(dash_res["category_table"]["rows"]))
    for r in dash_res["category_table"]["rows"]:
        print(" ", r)
    print("Brand Table Top 3:", dash_res["brand_table"]["rows"][:3])
    print("Branch Table:", dash_res["branch_table"]["rows"])
    print("Heatmap Rows:", len(dash_res["heatmap"]["rows"]))

    # 3. Alerts
    alerts_res = await app_module.get_alerts_data(app_module.AlertFilterRequest())
    print("\n--- ALERTS ---")
    print("KPIs:", alerts_res["kpis"])
    print("Total Alerts:", len(alerts_res["alerts"]))

    # 4. Comparison (Weekly)
    comp_res = await app_module.get_comparison_data(app_module.ComparisonFilterRequest())
    print("\n--- COMPARISON (Weekly) ---")
    print("Active weeks:", comp_res["filters"]["active_weeks"])
    print("KPIs:", comp_res["kpis"])
    print("Category Evolution points:", len(comp_res["charts"]["cat_evolution"]))
    print("Cat Matrix Columns:", comp_res["matrices"]["cat_matrix"]["columns"])
    print("Cat Matrix Rows count:", len(comp_res["matrices"]["cat_matrix"]["rows"]))

    # 5. Trend
    trend_res = await app_module.get_trend_data(app_module.TrendFilterRequest())
    print("\n--- TREND ---")
    print("KPIs:", trend_res["kpis"])
    print("Trajectory points:", len(trend_res["charts"]["trajectory"]))
    print("Pareto points:", len(trend_res["charts"]["pareto"]))
    print("Health Profile points:", len(trend_res["charts"]["composition"]))
    print("Branch Breakdown points:", len(trend_res["charts"]["branch_breakdown"]))
    print("Leaderboard rows:", len(trend_res["leaderboard"]))

asyncio.run(test_july())

