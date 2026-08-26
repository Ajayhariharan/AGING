@echo off
echo ===================================================
echo Starting Inventory Aging Dashboard (FastAPI + Vite)
echo ===================================================

echo [1/2] Launching FastAPI Backend (http://127.0.0.1:8000)...
start "Backend (FastAPI)" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --port 8000 --reload"

echo [2/2] Launching React + Vite Frontend (http://localhost:5173)...
start "Frontend (Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Application launched!
echo Access the frontend at: http://localhost:5173
echo Access the API documentation at: http://127.0.0.1:8000/docs
echo ===================================================

