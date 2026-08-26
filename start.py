import os
import sys
import subprocess
import time

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("==================================================")
    print("  Starting Mondelēz Inventory Dashboard Servers  ")
    print("==================================================")
    
    # 1. Start FastAPI backend
    print("\n[1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=backend_dir
    )

    time.sleep(1.5)

    # 2. Start Vite frontend
    print("\n[2/2] Launching Vite React Frontend on http://localhost:5173 ...")
    try:
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            shell=True
        )
    except Exception as e:
        print(f"Error launching frontend: {e}")
        backend_proc.terminate()
        return

    print("\n✓ Both servers are running!")
    print("  -> UI: http://localhost:5173")
    print("  -> API: http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to stop both servers.")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()

