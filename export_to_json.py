"""
export_to_json.py — One-time DB export script for EDai Incentives Model
========================================================================
Run this script on a machine with a live PostgreSQL connection (e.g., your
Windows dev machine with the project venv activated) to refresh the bundled
JSON data files in sql_data_cache/.

Usage:
    cd edai_accounting_modules
    python export_to_json.py

Prerequisites:
    - .env file present with DATABASE_URL set
    - psycopg2-binary and sqlalchemy installed (both are in requirements.txt)

Output:
    One JSON file per table in sql_data_cache/, named <table_name>.json
    Format: pandas orient='columns' (column → {row_index → value})
    This format is read directly by pd.read_json() in data_store.py.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment or .env file.")
    sys.exit(1)

try:
    from sqlalchemy import create_engine, inspect
    import pandas as pd
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}")
    print("Run: pip install sqlalchemy psycopg2-binary pandas python-dotenv")
    sys.exit(1)

# ── Output directory ────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent / "sql_data_cache"
CACHE_DIR.mkdir(exist_ok=True)

# ── Connect ──────────────────────────────────────────────────────────────────
print(f"Connecting to database...")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("✓ Connected successfully.\n")
except Exception as e:
    print(f"ERROR: Could not connect to database — {e}")
    sys.exit(1)

# ── Discover all tables ──────────────────────────────────────────────────────
inspector = inspect(engine)
all_tables = inspector.get_table_names()
print(f"Found {len(all_tables)} tables in database:\n")
for t in sorted(all_tables):
    print(f"  {t}")

print()

# ── Export each table ─────────────────────────────────────────────────────────
exported = []
failed = []

for table in sorted(all_tables):
    out_path = CACHE_DIR / f"{table}.json"
    try:
        df = pd.read_sql_table(table_name=table, con=engine)
        row_count = len(df)

        # Write using default orient='columns' so pd.read_json() can load it directly
        df.to_json(out_path, orient='columns', indent=2)

        print(f"  ✓  {table:<55}  {row_count:>6,} rows  →  {out_path.name}")
        exported.append((table, row_count))
    except Exception as e:
        print(f"  ✗  {table:<55}  ERROR: {e}")
        failed.append((table, str(e)))

engine.dispose()

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"Export complete: {len(exported)} tables exported, {len(failed)} failed.")
print(f"Output directory: {CACHE_DIR}")
total_size_mb = sum(os.path.getsize(CACHE_DIR / f"{t}.json") for t, _ in exported) / 1024 / 1024
print(f"Total size: {total_size_mb:.1f} MB")

if failed:
    print(f"\nFailed tables:")
    for t, err in failed:
        print(f"  {t}: {err}")

print("""
Next steps:
  1. Commit the updated sql_data_cache/ files to the repo.
  2. data_store.py will load from these JSON files automatically.
  3. No database connection is needed after this export.
""")
