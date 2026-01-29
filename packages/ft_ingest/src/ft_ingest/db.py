from __future__ import annotations
import sqlite3
from pathlib import Path

def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON;")
    return con

def init_schema(con: sqlite3.Connection, schema_sql_path: str) -> None:
    sql = Path(schema_sql_path).read_text(encoding="utf-8")
    con.executescript(sql)
    con.commit()
