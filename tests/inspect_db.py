import os
import sys
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'inventory.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, filename, uploaded_at, is_active FROM _files_history")
print("Files in history:")
for r in cursor.fetchall():
    print(r)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("\nAll SQLite Tables:", tables)

for t in tables:
    if t.startswith('f_'):
        df = pd.read_sql(f"SELECT * FROM {t} LIMIT 5", conn)
        print(f"\nTable {t} columns:", list(df.columns)[:8])
        for c in df.columns:
            if 'week' in c.lower() or 'wk' in c.lower():
                u_weeks = pd.read_sql(f"SELECT DISTINCT \"{c}\" FROM {t}", conn)
                print(f"  Week col [{c}]:", u_weeks.values.flatten())
            if 'mt' in c.lower() or 'channel' in c.lower():
                u_ch = pd.read_sql(f"SELECT DISTINCT \"{c}\" FROM {t}", conn)
                print(f"  Channel col [{c}]:", u_ch.values.flatten())

