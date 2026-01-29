from __future__ import annotations
import sqlite3
from pathlib import Path
from .build import Edge

def _player_label(con: sqlite3.Connection, pid: int) -> str:
    row = con.execute("SELECT name FROM player WHERE id = ?", (pid,)).fetchone()
    return row[0] if row else f"player_{pid}"

def export_dgs(
    con: sqlite3.Connection,
    edges: list[Edge],
    out_path: str,
    graph_name: str = "players"
) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Collect nodes used
    node_ids = set()
    for e in edges:
        node_ids.add(e.u)
        node_ids.add(e.v)

    with out.open("w", encoding="utf-8", newline="\n") as f:
        # Header: DGS version on its own line, then graph name + time bounds
        f.write("DGS004\n")
        f.write(f"{graph_name} 0 0\n")

        # Add nodes with labels
        for pid in sorted(node_ids):
            label = _player_label(con, pid).replace('"', '\\"')
            f.write(f'an "p{pid}" label:"{label}"\n')

        # Add edges with weight attribute
        for e in edges:
            eid = f"e_p{e.u}_p{e.v}"
            f.write(f'ae "{eid}" "p{e.u}" "p{e.v}" weight:{e.weight}\n')
