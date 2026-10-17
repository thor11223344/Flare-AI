"""Data-access layer. SQLite locally; Db2 for z/OS (ibm_db) when DB_BACKEND=db2.

All other modules go through read_table / write_table / query so the backend is swappable
with one environment variable and no code changes.
"""
import sqlite3
import pandas as pd
from src import config


def _connect():
    if config.DB_BACKEND == "db2":
        import ibm_db_dbi  # type: ignore  # pip install ibm_db
        return ibm_db_dbi.connect(config.DB2_DSN, "", "")
    return sqlite3.connect(config.SQLITE_PATH)


def write_table(df: pd.DataFrame, name: str) -> None:
    if config.DB_BACKEND == "db2":
        raise NotImplementedError("Load Db2 tables with the DDL in src/ibmz/db2_ddl.sql "
                                  "(LOAD utility / bulk insert); pipeline reads from Db2.")
    with _connect() as con:
        df.to_sql(name, con, if_exists="replace", index=False)


def read_table(name: str) -> pd.DataFrame:
    return query(f"SELECT * FROM {name}")


def query(sql: str, params=None) -> pd.DataFrame:
    con = _connect()
    try:
        return pd.read_sql(sql, con, params=params)
    finally:
        con.close()


def table_exists(name: str) -> bool:
    try:
        query(f"SELECT 1 FROM {name} LIMIT 1")
        return True
    except Exception:
        return False
