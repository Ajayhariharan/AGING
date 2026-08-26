import sys
import os
import asyncio

backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_dir)
import main as app_module
import database as db

async def verify_all():
    app_module.startup_init()
    
    print("========================================")
    print("1. VERIFYING JUNE WORKBOOK (file_id = 1)")
    print("========================================")
    db.load_file_into_cache(1)
    
    dash_june = await app_module.get_dashboard_data(app_module.DashboardFilterRequest())
    print("Dashboard High Risk (Cr):", dash_june['risk_cards']['high_risk_cr'], "Med Risk (Cr):", dash_june['risk_cards']['med_risk_cr'])
    print("Channel Filter Options:", dash_june['filters']['channel_options'])
    print("Branch Filter Options:", dash_june['filters']['branch_options'])
    
    comp_june_weekly = await app_module.get_comparison_data(app_module.ComparisonFilterRequest(mode="weekly"))
    print("Comparison Weekly Active Weeks:", comp_june_weekly['filters']['active_weeks'])
    print("Cat Matrix Columns:", comp_june_weekly['matrices']['cat_matrix']['columns'])

    print("\n========================================")
    print("2. VERIFYING JULY WORKBOOK (file_id = 3)")
    print("========================================")
    db.load_file_into_cache(3)

    dash_july = await app_module.get_dashboard_data(app_module.DashboardFilterRequest())
    print("Dashboard High Risk (Cr):", dash_july['risk_cards']['high_risk_cr'], "Med Risk (Cr):", dash_july['risk_cards']['med_risk_cr'])
    print("Category Table Rows:", len(dash_july['category_table']['rows']))
    print("Top 10 Brands Table Rows:", len(dash_july['brand_table']['rows']))
    print("DC Heatmap Rows:", len(dash_july['heatmap']['rows']), "Depots:", len(dash_july['heatmap']['columns'])-1)

    comp_july_weekly = await app_module.get_comparison_data(app_module.ComparisonFilterRequest(mode="weekly"))
    print("Comparison (Single Week 1) KPIs:", comp_july_weekly['kpis'])
    print("Cat Matrix Columns (Single Week):", comp_july_weekly['matrices']['cat_matrix']['columns'])

    print("\n========================================")
    print("3. VERIFYING MONTHLY COMPARISON (JUNE VS JULY)")
    print("========================================")
    comp_monthly = await app_module.get_comparison_data(app_module.ComparisonFilterRequest(mode="monthly"))
    print("Periods:", comp_monthly['filters']['active_weeks'])
    print("KPIs:", comp_monthly['kpis'])
    print("Branch Options:", comp_monthly['filters']['branch_options'])
    print("Monthly Cat Matrix Columns:", comp_monthly['matrices']['cat_matrix']['columns'])
    for row in comp_monthly['matrices']['cat_matrix']['rows']:
        print(" ", row)

asyncio.run(verify_all())

