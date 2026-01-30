from __future__ import annotations
import sqlite3
from dataclasses import dataclass

@dataclass(frozen=True)
class Edge:
    u: int
    v: int
    weight: int

def compute_edges(
    con: sqlite3.Connection,
    match_ids: list[int] | None = None,
    *,
    min_edge_weight: int = 1,
    min_minutes: int | None = None,
    starters_only: bool = False,
    positions: list[str] | None = None,
    nationalities: list[str] | None = None,
    name_query: str | None = None,
    competitions: list[str] | None = None,
    same_team_only: bool = False,
) -> list[Edge]:
    where = ["1=1"]
    params: list = []

    if match_ids:
        where.append(f"a.match_id IN ({','.join(['?'] * len(match_ids))})")
        params.extend(match_ids)

    if competitions:
        where.append(f"m.competition IN ({','.join(['?'] * len(competitions))})")
        params.extend(competitions)

    if min_minutes is not None:
        where.append("a.minutes >= ?")
        params.append(min_minutes)

    if starters_only:
        where.append("a.is_starter = 1")

    if positions:
        where.append(f"a.position IN ({','.join(['?'] * len(positions))})")
        params.extend(positions)

    if nationalities:
        where.append(f"p.nationality IN ({','.join(['?'] * len(nationalities))})")
        params.extend(nationalities)

    if name_query:
        where.append("p.name LIKE ?")
        params.append(f"%{name_query}%")

    team_cond = "AND a1.team_id = a2.team_id" if same_team_only else ""
    where_sql = " AND ".join(where)

    q = f"""
    WITH filtered AS (
        SELECT a.match_id, a.player_id, a.team_id
        FROM appearance a
        JOIN player p ON p.id = a.player_id
        JOIN match m ON m.id = a.match_id
        WHERE {where_sql}
    )
    SELECT a1.player_id AS u,
           a2.player_id AS v,
           COUNT(*) AS w
    FROM filtered a1
    JOIN filtered a2
      ON a1.match_id = a2.match_id
     AND a1.player_id < a2.player_id
     {team_cond}
    GROUP BY a1.player_id, a2.player_id
    HAVING COUNT(*) >= ?
    """

    params.append(min_edge_weight)
    cur = con.execute(q, tuple(params))
    return [Edge(u=row[0], v=row[1], weight=row[2]) for row in cur.fetchall()]
