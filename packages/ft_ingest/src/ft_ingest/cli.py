from __future__ import annotations
import argparse
from pathlib import Path

from ft_ingest.db import connect, init_schema
from ft_ingest.providers.statsbomb_open_data import StatsBombOpenData

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--team", action="append", required=True)
    args = ap.parse_args()

    con = connect(args.db)
    init_schema(con, str(Path(__file__).with_name("schema.sql")))

    provider = StatsBombOpenData()

    # Fetch matches for the given teams and date range
    matches = provider.list_matches(args.team, args.date_from, args.date_to)
    
    for match in matches:
        # Upsert home team
        con.execute(
            """
            INSERT INTO team (name, country, source, source_team_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source, source_team_id) DO UPDATE SET
                name = excluded.name
            """,
            (match.home.name, match.home.country, match.home.source, match.home.source_team_id),
        )
        home_team_id = con.execute(
            "SELECT id FROM team WHERE source = ? AND source_team_id = ?",
            (match.home.source, match.home.source_team_id),
        ).fetchone()[0]
        
        # Upsert away team
        con.execute(
            """
            INSERT INTO team (name, country, source, source_team_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source, source_team_id) DO UPDATE SET
                name = excluded.name
            """,
            (match.away.name, match.away.country, match.away.source, match.away.source_team_id),
        )
        away_team_id = con.execute(
            "SELECT id FROM team WHERE source = ? AND source_team_id = ?",
            (match.away.source, match.away.source_team_id),
        ).fetchone()[0]
        
        # Upsert match
        con.execute(
            """
            INSERT INTO match (match_date, season, competition, home_team_id, away_team_id, source, source_match_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_match_id) DO UPDATE SET
                match_date = excluded.match_date,
                season = excluded.season,
                competition = excluded.competition
            """,
            (match.match_date, match.season, match.competition, home_team_id, away_team_id, match.source, match.source_match_id),
        )
        match_id = con.execute(
            "SELECT id FROM match WHERE source = ? AND source_match_id = ?",
            (match.source, match.source_match_id),
        ).fetchone()[0]
        
        # Get and upsert lineups/appearances
        appearances = provider.get_lineups(match.source_match_id)
        for appearance in appearances:
            # Upsert player
            con.execute(
                """
                INSERT INTO player (name, birth_date, nationality, source, source_player_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, source_player_id) DO UPDATE SET
                    name = excluded.name
                """,
                (appearance.player.name, appearance.player.birth_date, appearance.player.nationality, appearance.player.source, appearance.player.source_player_id),
            )
            player_id = con.execute(
                "SELECT id FROM player WHERE source = ? AND source_player_id = ?",
                (appearance.player.source, appearance.player.source_player_id),
            ).fetchone()[0]
            
            # Upsert team (in case it wasn't in match home/away)
            con.execute(
                """
                INSERT INTO team (name, country, source, source_team_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source, source_team_id) DO UPDATE SET
                    name = excluded.name
                """,
                (appearance.team.name, appearance.team.country, appearance.team.source, appearance.team.source_team_id),
            )
            team_id = con.execute(
                "SELECT id FROM team WHERE source = ? AND source_team_id = ?",
                (appearance.team.source, appearance.team.source_team_id),
            ).fetchone()[0]
            
            # Upsert appearance
            con.execute(
                """
                INSERT INTO appearance (match_id, player_id, team_id, is_starter, minutes, position)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id, player_id) DO UPDATE SET
                    is_starter = excluded.is_starter,
                    minutes = excluded.minutes,
                    position = excluded.position
                """,
                (match_id, player_id, team_id, int(appearance.is_starter), appearance.minutes, appearance.position),
            )
        
        con.commit()
        print(f"Ingested match: {match.home.name} vs {match.away.name} ({match.match_date})")

if __name__ == "__main__":
    main()
