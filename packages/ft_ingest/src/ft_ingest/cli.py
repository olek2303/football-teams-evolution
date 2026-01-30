from __future__ import annotations
import argparse
import structlog
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from ft_ingest.db import connect, init_schema
from ft_ingest.providers import FootballiaProvider, StatsBombOpenData

# Global lock for database writes to prevent "database is locked" errors
_db_lock = Lock()

def main():
    log = structlog.get_logger("ft-ingest")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--team", action="append", help="Team name(s) to fetch (required if --links-file not provided)")
    ap.add_argument(
        "--links-file",
        help="Path to file with match links (one per line). If provided, --team is ignored.",
    )
    ap.add_argument(
        "--provider",
        default="statsbomb",
        choices=["statsbomb", "footballia"],
        help="Data provider to use",
    )
    args = ap.parse_args()

    if not args.team and not args.links_file:
        ap.error("Either --team or --links-file must be provided")

    # Resolve db path to absolute path to ensure consistency across threads
    db_path = str(Path(args.db).resolve())
    log.info("database.path", db_path=db_path)

    con = connect(db_path)
    init_schema(con, str(Path(__file__).with_name("schema.sql")))
    
    # Enable WAL mode for better concurrent access
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    con.commit()
    con.close()

    if args.provider == "footballia":
        provider = FootballiaProvider()
    else:
        provider = StatsBombOpenData()

    # Fetch matches either from provider or from links file
    if args.links_file:
        log.info("fetch_matches.from_file", links_file=args.links_file)
        matches = _fetch_matches_from_links_file(args.links_file, args.date_from, args.date_to, provider)
    else:
        log.info("fetch_matches.start", provider=args.provider, teams=args.team)
        matches = provider.list_matches(args.team, args.date_from, args.date_to)
    
    log.info("fetch_matches.done", match_count=len(matches))
    
    # Batch insert using thread pool for parallel DB operations
    log.info("ingest_matches.start", match_count=len(matches))
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_ingest_match, db_path, provider, match)
            for match in matches
        ]
        for i, future in enumerate(futures, 1):
            try:
                future.result()
                if i % 10 == 0:
                    log.info("ingest_matches.progress", ingested=i, total=len(matches))
            except Exception as e:
                log.error("ingest_matches.error", match_num=i, error=str(e))
    
    log.info("ingest_matches.done", total=len(matches))

def _fetch_matches_from_links_file(links_file: str, date_from: str, date_to: str, provider):
    """Load match links from file and fetch metadata for each."""
    log = structlog.get_logger("ft-ingest")
    from ft_ingest.providers.base import MatchDTO, TeamDTO
    
    # Read links from file
    links = []
    try:
        with open(links_file, "r") as f:
            links = [line.strip() for line in f if line.strip()]
    except Exception as e:
        log.error("links_file.read_error", file=links_file, error=str(e))
        return []
    
    log.info("links_file.loaded", file=links_file, link_count=len(links))
    
    # Fetch metadata for each link in parallel
    log.info("fetch_matches_from_links.start", link_count=len(links))
    date_from_obj = None
    date_to_obj = None
    if hasattr(provider, "_parse_iso_date"):
        date_from_obj = provider._parse_iso_date(date_from)
        date_to_obj = provider._parse_iso_date(date_to)
    
    matches = []
    seen_matches = set()
    processed = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all metadata fetch tasks
        future_to_link = {
            executor.submit(provider._scrape_match_metadata, link): link
            for link in links
        }
        
        # Process results as they complete
        for future in as_completed(future_to_link):
            processed += 1
            link = future_to_link[future]
            
            match_id = provider._match_id_from_url(link)
            if match_id in seen_matches:
                continue
            
            try:
                meta = future.result()
            except Exception as e:
                log.warn("fetch_matches_from_links.error", url=link, error=str(e))
                continue
            
            if not meta or not meta.get("match_date"):
                continue
            
            # Check date range if parser available
            if hasattr(provider, "_date_in_range") and date_from_obj and date_to_obj:
                if not provider._date_in_range(meta["match_date"], date_from_obj, date_to_obj):
                    log.info("fetch_matches_from_links.out_of_range", date=meta["match_date"])
                    continue
            
            home_team = TeamDTO(
                source=provider.name,
                source_team_id=meta["home_team_id"],
                name=meta["home_team_name"],
            )
            away_team = TeamDTO(
                source=provider.name,
                source_team_id=meta["away_team_id"],
                name=meta["away_team_name"],
            )
            
            match = MatchDTO(
                source=provider.name,
                source_match_id=match_id,
                match_date=meta["match_date"],
                season=meta.get("season"),
                competition=meta.get("competition"),
                home=home_team,
                away=away_team,
            )
            matches.append(match)
            seen_matches.add(match_id)
            
            if processed % 50 == 0:
                log.info("fetch_matches_from_links.progress", processed=processed, total=len(future_to_link), matches_found=len(matches))
    
    log.info("fetch_matches_from_links.done", match_count=len(matches))
    return matches

def _ingest_match(db_path, provider, match):
    """Ingest a single match with its lineups into the database.
    
    Creates a new connection per thread since SQLite connections cannot be shared.
    Uses a global lock to prevent concurrent writes.
    """
    with _db_lock:
        con = connect(db_path)
        try:
            # Set busy timeout for this connection
            con.execute("PRAGMA busy_timeout=30000")
            
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
        finally:
            con.close()

if __name__ == "__main__":
    main()
