"""Db2 for z/OS bulk data loader.
Reads SQLite/CSV tables and executes bulk insert into Db2 tables based on db2_ddl.sql.
Includes dry-run mode and strict credentials check.
"""
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from src import config
from src.data import db

TABLES = ["tracts", "tract_year", "policies", "risk_scores"]


def get_ddl_statements() -> List[str]:
    """Parse DDL statements from src/ibmz/db2_ddl.sql."""
    ddl_file = config.ROOT / "src" / "ibmz" / "db2_ddl.sql"
    if not ddl_file.exists():
        raise FileNotFoundError(f"DDL file not found at {ddl_file}")

    content = ddl_file.read_text()
    # Split by semicolon and ignore comments/empty lines
    statements = []
    for chunk in content.split(";"):
        lines = [line.strip() for line in chunk.splitlines() if line.strip() and not line.strip().startswith("--")]
        stmt = " ".join(lines).strip()
        if stmt and stmt.upper().startswith(("CREATE TABLE", "CREATE INDEX")):
            statements.append(stmt + ";")
    return statements


def generate_insert_sql(table_name: str, columns: List[str]) -> str:
    """Generate parameterized SQL INSERT for Db2 table."""
    db2_table = f"WILDFIRE.{table_name.upper()}"
    col_str = ", ".join([c.upper() for c in columns])
    placeholders = ", ".join(["?"] * len(columns))
    return f"INSERT INTO {db2_table} ({col_str}) VALUES ({placeholders})"


def load_tables_data() -> Dict[str, pd.DataFrame]:
    """Load local data from SQLite or CSV for all tables."""
    data = {}
    for tbl in TABLES:
        try:
            df = db.read_table(tbl)
            data[tbl] = df
        except Exception as e:
            print(f"[db2_load] Warning: Could not read table '{tbl}' ({e})")
    return data


def run_db2_load(dry_run: bool = False, verbose: bool = True) -> Dict[str, Any]:
    """Execute Db2 load process or dry-run validation."""
    data = load_tables_data()
    ddl_stmts = get_ddl_statements()
    dsn = os.getenv("DB2_DSN", "")

    summary = {
        "dry_run": dry_run,
        "tables_found": list(data.keys()),
        "row_counts": {k: len(v) for k, v in data.items()},
        "ddl_statements_count": len(ddl_stmts),
    }

    if dry_run or not dsn:
        if verbose:
            print("=" * 65)
            print("IBM Db2 for z/OS BULK LOADER (DRY-RUN MODE)")
            print("=" * 65)
            print(f"Db2 DSN Configured: {'YES' if dsn else 'NO (Missing DB2_DSN env var)'}")
            print("\n[DDL Statements to execute in Db2 subsystem]:")
            for stmt in ddl_stmts:
                print(f"  {stmt}")

            print("\n[Parameterized INSERT statements and payload volumes]:")
            for tbl, df in data.items():
                cols = list(df.columns)
                insert_sql = generate_insert_sql(tbl, cols)
                print(f"\n  Table: WILDFIRE.{tbl.upper()} ({len(df):,} rows)")
                print(f"  SQL:   {insert_sql}")
                if len(df) > 0:
                    sample_row = [str(x) for x in df.iloc[0].values]
                    print(f"  Sample row [0]: ({', '.join(sample_row[:5])}...)")

            print("\n" + "=" * 65)
            if not dsn:
                print("NOTE: Set DB2_DSN environment variable with valid z/OS credentials")
                print("to execute live ingestion. Running without credentials is prevented.")
            print("=" * 65)
        return summary

    # Live connection execution
    try:
        import ibm_db_dbi  # type: ignore
    except ImportError:
        raise ImportError("ibm_db package not installed. Install via `pip install ibm_db` for live z/OS connectivity.")

    print(f"[db2_load] Connecting to Db2 for z/OS via DSN...")
    conn = ibm_db_dbi.connect(dsn, "", "")
    cursor = conn.cursor()

    try:
        # 1. Execute DDL
        for stmt in ddl_stmts:
            try:
                cursor.execute(stmt.rstrip(";"))
            except Exception as e:
                # Table may already exist
                if verbose:
                    print(f"[db2_load] DDL note: {e}")

        # 2. Bulk insert data using executemany
        for tbl, df in data.items():
            if df.empty:
                continue
            cols = list(df.columns)
            sql = generate_insert_sql(tbl, cols)
            rows = [tuple(x) for x in df.values]
            cursor.executemany(sql, rows)
            print(f"[db2_load] Inserted {len(rows):,} rows into WILDFIRE.{tbl.upper()}")

        conn.commit()
        print("[db2_load] Ingestion committed successfully.")
        summary["status"] = "SUCCESS"
        return summary
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk insert tables into IBM Db2 for z/OS")
    parser.add_argument("--dry-run", action="store_true", help="Print DDL and parameterized SQL statements without executing")
    args = parser.parse_args()

    run_db2_load(dry_run=args.dry_run or not os.getenv("DB2_DSN"))
