"""Database abstraction: SQLite locally, Db2 for z/OS via ibm_db (DB_BACKEND=db2).

Db2 settings (env): DB2_DSN = "DATABASE=...;HOSTNAME=...;PORT=...;PROTOCOL=TCPIP;UID=...;PWD=...;SECURITY=SSL;"
NOTE: the Db2 path is written to the ibm_db_dbi DB-API but could not be tested without a Db2 instance.
"""
import os
import sqlite3
import pandas as pd
from src import config as C


class SQLiteDB:
    name = "sqlite"

    def __init__(self):
        self.path = C.SQLITE_PATH

    def exists(self):
        return self.path.exists()

    def read(self, sql, params=None):
        with sqlite3.connect(self.path) as con:
            return pd.read_sql_query(sql, con, params=params)

    def write(self, df, table):
        with sqlite3.connect(self.path) as con:
            df.to_sql(table, con, if_exists="replace", index=False, chunksize=50_000)

    def index(self, table, col):
        with sqlite3.connect(self.path) as con:
            con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col})")


class Db2DB:
    name = "db2"

    def __init__(self):
        import ibm_db_dbi  # lazy import so SQLite users don't need it
        self._dbi = ibm_db_dbi
        self.dsn = os.environ["DB2_DSN"]
        self.schema = os.getenv("DB2_SCHEMA", "WILDFIRE")

    def _con(self):
        return self._dbi.connect(self.dsn, "", "")

    def exists(self):
        try:
            self.read(f"SELECT 1 FROM {self.schema}.TRACTS FETCH FIRST 1 ROWS ONLY")
            return True
        except Exception:
            return False

    def read(self, sql, params=None):
        con = self._con()
        try:
            df = pd.read_sql(sql, con, params=params)
            df.columns = [c.lower() for c in df.columns]
            return df
        finally:
            con.close()

    def write(self, df, table):
        def sqltype(s):
            if pd.api.types.is_integer_dtype(s) or pd.api.types.is_bool_dtype(s):
                return "BIGINT"
            if pd.api.types.is_float_dtype(s):
                return "DOUBLE"
            return "VARCHAR(2000)"
        full = f"{self.schema}.{table.upper()}"
        con = self._con()
        try:
            cur = con.cursor()
            try:
                cur.execute(f"DROP TABLE {full}")
            except Exception:
                pass
            cols = ", ".join(f'"{c.upper()}" {sqltype(df[c])}' for c in df.columns)
            cur.execute(f"CREATE TABLE {full} ({cols})")
            ph = ", ".join("?" for _ in df.columns)
            rows = [tuple(None if pd.isna(v) else (int(v) if isinstance(v, bool) else v) for v in r)
                    for r in df.itertuples(index=False, name=None)]
            cur.executemany(f"INSERT INTO {full} VALUES ({ph})", rows)
            con.commit()
        finally:
            con.close()

    def index(self, table, col):
        pass  # create indexes with src/ibmz/ddl.sql on Db2


def get_db():
    return Db2DB() if C.DB_BACKEND == "db2" else SQLiteDB()


def tname(db, table):
    """Table name with schema for Db2."""
    return f"{db.schema}.{table.upper()}" if db.name == "db2" else table
