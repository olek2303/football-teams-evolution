"""Populate the football database with mock data for development."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

# Mock data
TEAMS = [
    ("Liverpool", "England", "statsbomb_open_data", "1"),
    ("AS Roma", "Italy", "statsbomb_open_data", "87"),
    ("Manchester United", "England", "statsbomb_open_data", "2"),
    ("Arsenal", "England", "statsbomb_open_data", "3"),
    ("Chelsea", "England", "statsbomb_open_data", "4"),
    ("AC Milan", "Italy", "statsbomb_open_data", "98"),
    ("Inter Milan", "Italy", "statsbomb_open_data", "103"),
]

PLAYERS = [
    ("Mohamed Salah", "1992-06-15", "Egypt", "statsbomb_open_data", "5203"),
    ("Sadio Mané", "1992-04-10", "Senegal", "statsbomb_open_data", "5206"),
    ("Virgil van Dijk", "1991-07-08", "Netherlands", "statsbomb_open_data", "5228"),
    ("Jordan Henderson", "1990-06-17", "England", "statsbomb_open_data", "5230"),
    ("Alisson Ramses Becker", "1992-10-02", "Brazil", "statsbomb_open_data", "5197"),
    ("Bruno Fernandes", "1994-09-08", "Portugal", "statsbomb_open_data", "5381"),
    ("Cristiano Ronaldo", "1985-02-05", "Portugal", "statsbomb_open_data", "5207"),
    ("Jadon Sancho", "2000-03-25", "England", "statsbomb_open_data", "5446"),
    ("Bukayo Saka", "2001-09-05", "England", "statsbomb_open_data", "5598"),
    ("Emile Smith Rowe", "2000-07-28", "England", "statsbomb_open_data", "5523"),
    ("Tammy Abraham", "1997-10-02", "England", "statsbomb_open_data", "5501"),
    ("Lorenzo Pellegrini", "1996-06-19", "Italy", "statsbomb_open_data", "5328"),
]


def populate_mock_data(db_path: str) -> None:
    """Populate database with mock data."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Insert teams
    team_ids = {}
    for name, country, source, source_id in TEAMS:
        cur.execute(
            """
            INSERT INTO team (name, country, source, source_team_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source, source_team_id) DO UPDATE SET
                name = excluded.name
            """,
            (name, country, source, source_id),
        )
        cur.execute(
            "SELECT id FROM team WHERE source = ? AND source_team_id = ?",
            (source, source_id),
        )
        team_ids[(source, source_id)] = cur.fetchone()[0]

    # Insert players
    player_ids = {}
    for name, birth_date, nationality, source, source_id in PLAYERS:
        cur.execute(
            """
            INSERT INTO player (name, birth_date, nationality, source, source_player_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source, source_player_id) DO UPDATE SET
                name = excluded.name
            """,
            (name, birth_date, nationality, source, source_id),
        )
        cur.execute(
            "SELECT id FROM player WHERE source = ? AND source_player_id = ?",
            (source, source_id),
        )
        player_ids[(source, source_id)] = cur.fetchone()[0]

    # Insert mock matches
    base_date = datetime(2021, 8, 1)
    match_data = [
        (0, 1, "2021-08-14", "2021/22", "Premier League"),  # Liverpool vs Man Utd
        (0, 2, "2021-08-21", "2021/22", "Premier League"),  # Liverpool vs Arsenal
        (1, 3, "2021-08-28", "2021/22", "Serie A"),  # AS Roma vs AC Milan
        (0, 4, "2021-09-04", "2021/22", "Premier League"),  # Liverpool vs Chelsea
        (3, 5, "2021-09-11", "2021/22", "Serie A"),  # AC Milan vs Inter Milan
        (1, 6, "2021-09-18", "2021/22", "Serie A"),  # AS Roma vs Inter Milan
    ]

    match_ids = []
    for home_idx, away_idx, match_date, season, competition in match_data:
        home_team = TEAMS[home_idx]
        away_team = TEAMS[away_idx]

        source = "statsbomb_open_data"
        source_match_id = f"match_{len(match_ids)}"

        home_team_db_id = team_ids[(source, home_team[3])]
        away_team_db_id = team_ids[(source, away_team[3])]

        cur.execute(
            """
            INSERT INTO match (match_date, season, competition, home_team_id, away_team_id, source, source_match_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_match_id) DO UPDATE SET
                match_date = excluded.match_date
            """,
            (
                match_date,
                season,
                competition,
                home_team_db_id,
                away_team_db_id,
                source,
                source_match_id,
            ),
        )
        cur.execute(
            "SELECT id FROM match WHERE source = ? AND source_match_id = ?",
            (source, source_match_id),
        )
        match_ids.append(cur.fetchone()[0])

    # Insert mock appearances
    appearance_data = [
        # Match 0: Liverpool vs Man Utd
        (0, ("statsbomb_open_data", "5203"), ("statsbomb_open_data", "1"), True, 90, "Right Wing"),
        (0, ("statsbomb_open_data", "5206"), ("statsbomb_open_data", "1"), True, 87, "Left Wing"),
        (0, ("statsbomb_open_data", "5228"), ("statsbomb_open_data", "1"), True, 90, "Center Back"),
        (0, ("statsbomb_open_data", "5207"), ("statsbomb_open_data", "2"), True, 90, "Right Wing"),
        (0, ("statsbomb_open_data", "5381"), ("statsbomb_open_data", "2"), True, 88, "Midfielder"),
        # Match 1: Liverpool vs Arsenal
        (1, ("statsbomb_open_data", "5203"), ("statsbomb_open_data", "1"), True, 90, "Right Wing"),
        (1, ("statsbomb_open_data", "5598"), ("statsbomb_open_data", "3"), True, 85, "Left Wing"),
        (1, ("statsbomb_open_data", "5523"), ("statsbomb_open_data", "3"), True, 90, "Midfielder"),
        # Match 2: AS Roma vs AC Milan
        (2, ("statsbomb_open_data", "5328"), ("statsbomb_open_data", "87"), True, 90, "Midfielder"),
        (2, ("statsbomb_open_data", "5501"), ("statsbomb_open_data", "87"), True, 89, "Forward"),
        # Match 3: Liverpool vs Chelsea
        (3, ("statsbomb_open_data", "5203"), ("statsbomb_open_data", "1"), True, 90, "Right Wing"),
        # Match 4: AC Milan vs Inter Milan
        (4, ("statsbomb_open_data", "5501"), ("statsbomb_open_data", "98"), True, 90, "Forward"),
        # Match 5: AS Roma vs Inter Milan
        (5, ("statsbomb_open_data", "5328"), ("statsbomb_open_data", "87"), True, 88, "Midfielder"),
    ]

    for match_idx, (player_source, player_id), (
        team_source,
        team_id,
    ), is_starter, minutes, position in appearance_data:
        match_db_id = match_ids[match_idx]
        player_db_id = player_ids[(player_source, player_id)]
        team_db_id = team_ids[(team_source, team_id)]

        cur.execute(
            """
            INSERT INTO appearance (match_id, player_id, team_id, is_starter, minutes, position)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, player_id) DO UPDATE SET
                is_starter = excluded.is_starter,
                minutes = excluded.minutes,
                position = excluded.position
            """,
            (match_db_id, player_db_id, team_db_id, int(is_starter), minutes, position),
        )

    con.commit()
    con.close()
    print(f"✓ Mock data populated in {db_path}")
    print(f"  - {len(TEAMS)} teams")
    print(f"  - {len(PLAYERS)} players")
    print(f"  - {len(match_ids)} matches")
    print(f"  - {len(appearance_data)} appearances")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "data" / "db" / "football.sqlite3"
    schema_path = project_root / "packages" / "ft_ingest" / "src" / "ft_ingest" / "schema.sql"

    # Initialize schema first
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    sql = schema_path.read_text(encoding="utf-8")
    con.executescript(sql)
    con.commit()
    con.close()

    populate_mock_data(str(db_path))
