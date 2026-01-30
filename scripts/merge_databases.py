"""
Merge football.sqlite3 with stats-bomb-football.sqlite3.

This script merges the two databases, prioritizing StatsBomb data when available
because it has more complete information (nationality, positions, minutes played).

Strategy:
1. Start with football.sqlite3 as the base
2. Add any new teams/players/matches from stats-bomb that don't exist in football
3. Update existing records with better StatsBomb data (nationality for players, 
   position/minutes for appearances)
4. Create a new merged database: football-merged.sqlite3
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def merge_databases(
    base_db: Path, 
    supplement_db: Path, 
    output_db: Path
):
    """
    Merge two databases, using supplement to enhance base.
    
    Args:
        base_db: Path to football.sqlite3
        supplement_db: Path to stats-bomb-football.sqlite3
        output_db: Path to output merged database
    """
    log("Starting database merge...")
    
    # Create a copy of base database as starting point
    if output_db.exists():
        backup = output_db.with_suffix('.sqlite3.backup')
        log(f"Backing up existing merged database to {backup.name}")
        shutil.copy(output_db, backup)
        output_db.unlink()
    
    log(f"Copying {base_db.name} to {output_db.name}")
    shutil.copy(base_db, output_db)
    
    # Connect to both databases
    log("Connecting to databases...")
    merged_conn = sqlite3.connect(output_db)
    merged_conn.row_factory = sqlite3.Row
    merged_cursor = merged_conn.cursor()
    
    stats_conn = sqlite3.connect(supplement_db)
    stats_conn.row_factory = sqlite3.Row
    stats_cursor = stats_conn.cursor()
    
    try:
        # Step 1: Merge teams
        log("\n" + "="*60)
        log("STEP 1: Merging teams")
        log("="*60)
        merge_teams(merged_cursor, stats_cursor, merged_conn)
        
        # Step 2: Merge players
        log("\n" + "="*60)
        log("STEP 2: Merging players")
        log("="*60)
        merge_players(merged_cursor, stats_cursor, merged_conn)
        
        # Step 3: Merge matches
        log("\n" + "="*60)
        log("STEP 3: Merging matches")
        log("="*60)
        merge_matches(merged_cursor, stats_cursor, merged_conn)
        
        # Step 4: Merge appearances
        log("\n" + "="*60)
        log("STEP 4: Merging appearances")
        log("="*60)
        merge_appearances(merged_cursor, stats_cursor, merged_conn)
        
        # Final statistics
        log("\n" + "="*60)
        log("MERGE COMPLETE - Final Statistics")
        log("="*60)
        print_statistics(merged_cursor)
        
    finally:
        stats_conn.close()
        merged_conn.close()
    
    log(f"\n✓ Merged database saved to: {output_db}")

def merge_teams(merged_cursor, stats_cursor, merged_conn):
    """Merge team data from StatsBomb into merged database."""
    
    # Get all teams from statsbomb
    stats_cursor.execute("""
        SELECT id, name, country, source, source_team_id 
        FROM team
    """)
    
    teams_added = 0
    teams_updated = 0
    
    for row in stats_cursor.fetchall():
        # Check if team exists by source and source_team_id
        merged_cursor.execute("""
            SELECT id, country FROM team 
            WHERE source = ? AND source_team_id = ?
        """, (row['source'], row['source_team_id']))
        
        existing = merged_cursor.fetchone()
        
        if existing:
            # Update if StatsBomb has country and merged doesn't
            if row['country'] and not existing['country']:
                merged_cursor.execute("""
                    UPDATE team SET country = ? 
                    WHERE id = ?
                """, (row['country'], existing['id']))
                teams_updated += 1
        else:
            # Insert new team
            merged_cursor.execute("""
                INSERT INTO team (name, country, source, source_team_id)
                VALUES (?, ?, ?, ?)
            """, (row['name'], row['country'], row['source'], row['source_team_id']))
            teams_added += 1
    
    merged_conn.commit()
    log(f"  ✓ Teams added: {teams_added}")
    log(f"  ✓ Teams updated with country info: {teams_updated}")

def merge_players(merged_cursor, stats_cursor, merged_conn):
    """Merge player data from StatsBomb into merged database."""
    
    # Get all players from statsbomb
    stats_cursor.execute("""
        SELECT id, name, birth_date, nationality, source, source_player_id 
        FROM player
    """)
    
    players_added = 0
    players_updated = 0
    
    for row in stats_cursor.fetchall():
        # Check if player exists by source and source_player_id
        merged_cursor.execute("""
            SELECT id, birth_date, nationality FROM player 
            WHERE source = ? AND source_player_id = ?
        """, (row['source'], row['source_player_id']))
        
        existing = merged_cursor.fetchone()
        
        if existing:
            # Update with StatsBomb data if it has info that merged doesn't
            updates = []
            params = []
            
            if row['nationality'] and not existing['nationality']:
                updates.append("nationality = ?")
                params.append(row['nationality'])
            
            if row['birth_date'] and not existing['birth_date']:
                updates.append("birth_date = ?")
                params.append(row['birth_date'])
            
            if updates:
                params.append(existing['id'])
                sql = f"UPDATE player SET {', '.join(updates)} WHERE id = ?"
                merged_cursor.execute(sql, params)
                players_updated += 1
        else:
            # Insert new player
            merged_cursor.execute("""
                INSERT INTO player (name, birth_date, nationality, source, source_player_id)
                VALUES (?, ?, ?, ?, ?)
            """, (row['name'], row['birth_date'], row['nationality'], 
                  row['source'], row['source_player_id']))
            players_added += 1
    
    merged_conn.commit()
    log(f"  ✓ Players added: {players_added}")
    log(f"  ✓ Players updated with nationality/birth_date: {players_updated}")

def merge_matches(merged_cursor, stats_cursor, merged_conn):
    """Merge match data from StatsBomb into merged database."""
    
    # First, we need to create a mapping of StatsBomb team IDs to merged team IDs
    stats_cursor.execute("SELECT id, source, source_team_id FROM team")
    stats_teams = {row['id']: (row['source'], row['source_team_id']) 
                   for row in stats_cursor.fetchall()}
    
    team_id_map = {}
    for stats_id, (source, source_team_id) in stats_teams.items():
        merged_cursor.execute("""
            SELECT id FROM team WHERE source = ? AND source_team_id = ?
        """, (source, source_team_id))
        merged_team = merged_cursor.fetchone()
        if merged_team:
            team_id_map[stats_id] = merged_team['id']
    
    # Get all matches from statsbomb
    stats_cursor.execute("""
        SELECT id, match_date, season, competition, home_team_id, away_team_id, 
               source, source_match_id 
        FROM match
    """)
    
    matches_added = 0
    matches_updated = 0
    
    for row in stats_cursor.fetchall():
        # Map team IDs
        home_team_id = team_id_map.get(row['home_team_id'])
        away_team_id = team_id_map.get(row['away_team_id'])
        
        if not home_team_id or not away_team_id:
            continue  # Skip if teams not found
        
        # Check if match exists
        merged_cursor.execute("""
            SELECT id, season FROM match 
            WHERE source = ? AND source_match_id = ?
        """, (row['source'], row['source_match_id']))
        
        existing = merged_cursor.fetchone()
        
        if existing:
            # Update season if StatsBomb has it and merged doesn't
            if row['season'] and not existing['season']:
                merged_cursor.execute("""
                    UPDATE match SET season = ? WHERE id = ?
                """, (row['season'], existing['id']))
                matches_updated += 1
        else:
            # Insert new match
            merged_cursor.execute("""
                INSERT INTO match (match_date, season, competition, home_team_id, 
                                   away_team_id, source, source_match_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (row['match_date'], row['season'], row['competition'], 
                  home_team_id, away_team_id, row['source'], row['source_match_id']))
            matches_added += 1
    
    merged_conn.commit()
    log(f"  ✓ Matches added: {matches_added}")
    log(f"  ✓ Matches updated with season info: {matches_updated}")

def merge_appearances(merged_cursor, stats_cursor, merged_conn):
    """Merge appearance data from StatsBomb into merged database."""
    
    # Create mappings for teams, players, and matches
    log("  Creating ID mappings...")
    
    # Team mapping
    stats_cursor.execute("SELECT id, source, source_team_id FROM team")
    team_id_map = {}
    for row in stats_cursor.fetchall():
        merged_cursor.execute("""
            SELECT id FROM team WHERE source = ? AND source_team_id = ?
        """, (row['source'], row['source_team_id']))
        merged_team = merged_cursor.fetchone()
        if merged_team:
            team_id_map[row['id']] = merged_team['id']
    
    # Player mapping
    stats_cursor.execute("SELECT id, source, source_player_id FROM player")
    player_id_map = {}
    for row in stats_cursor.fetchall():
        merged_cursor.execute("""
            SELECT id FROM player WHERE source = ? AND source_player_id = ?
        """, (row['source'], row['source_player_id']))
        merged_player = merged_cursor.fetchone()
        if merged_player:
            player_id_map[row['id']] = merged_player['id']
    
    # Match mapping
    stats_cursor.execute("SELECT id, source, source_match_id FROM match")
    match_id_map = {}
    for row in stats_cursor.fetchall():
        merged_cursor.execute("""
            SELECT id FROM match WHERE source = ? AND source_match_id = ?
        """, (row['source'], row['source_match_id']))
        merged_match = merged_cursor.fetchone()
        if merged_match:
            match_id_map[row['id']] = merged_match['id']
    
    log("  Merging appearance records...")
    
    # Get all appearances from statsbomb
    stats_cursor.execute("""
        SELECT match_id, player_id, team_id, is_starter, minutes, position
        FROM appearance
    """)
    
    appearances_added = 0
    appearances_updated = 0
    
    for row in stats_cursor.fetchall():
        # Map IDs
        match_id = match_id_map.get(row['match_id'])
        player_id = player_id_map.get(row['player_id'])
        team_id = team_id_map.get(row['team_id'])
        
        if not match_id or not player_id or not team_id:
            continue  # Skip if any mapping failed
        
        # Check if appearance exists
        merged_cursor.execute("""
            SELECT match_id, player_id, minutes, position FROM appearance 
            WHERE match_id = ? AND player_id = ?
        """, (match_id, player_id))
        
        existing = merged_cursor.fetchone()
        
        if existing:
            # Update with StatsBomb data if it has info that merged doesn't
            updates = []
            params = []
            
            if row['minutes'] is not None and existing['minutes'] is None:
                updates.append("minutes = ?")
                params.append(row['minutes'])
            
            if row['position'] and not existing['position']:
                updates.append("position = ?")
                params.append(row['position'])
            
            if updates:
                params.extend([match_id, player_id])
                sql = f"UPDATE appearance SET {', '.join(updates)} WHERE match_id = ? AND player_id = ?"
                merged_cursor.execute(sql, params)
                appearances_updated += 1
        else:
            # Insert new appearance
            try:
                merged_cursor.execute("""
                    INSERT INTO appearance (match_id, player_id, team_id, is_starter, minutes, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (match_id, player_id, team_id, row['is_starter'], 
                      row['minutes'], row['position']))
                appearances_added += 1
            except sqlite3.IntegrityError:
                # Might happen if there are duplicate entries
                pass
    
    merged_conn.commit()
    log(f"  ✓ Appearances added: {appearances_added}")
    log(f"  ✓ Appearances updated with minutes/position: {appearances_updated}")

def print_statistics(cursor):
    """Print final database statistics."""
    
    cursor.execute("SELECT COUNT(*) as count FROM team")
    teams = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM player")
    players = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM player WHERE nationality IS NOT NULL")
    players_with_nationality = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM match")
    matches = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM appearance")
    appearances = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM appearance WHERE position IS NOT NULL")
    appearances_with_position = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM appearance WHERE minutes IS NOT NULL")
    appearances_with_minutes = cursor.fetchone()['count']
    
    log(f"  Teams: {teams:,}")
    log(f"  Players: {players:,}")
    log(f"    - With nationality: {players_with_nationality:,} ({players_with_nationality/players*100:.1f}%)")
    log(f"  Matches: {matches:,}")
    log(f"  Appearances: {appearances:,}")
    log(f"    - With position: {appearances_with_position:,} ({appearances_with_position/appearances*100:.1f}%)")
    log(f"    - With minutes: {appearances_with_minutes:,} ({appearances_with_minutes/appearances*100:.1f}%)")

def main():
    """Main entry point."""
    data_dir = Path("data/db")
    
    base_db = data_dir / "football.sqlite3"
    supplement_db = data_dir / "stats-bomb-football.sqlite3"
    output_db = data_dir / "football-merged.sqlite3"
    
    # Verify input files exist
    if not base_db.exists():
        print(f"ERROR: {base_db} not found!")
        return
    
    if not supplement_db.exists():
        print(f"ERROR: {supplement_db} not found!")
        return
    
    # Perform merge
    merge_databases(base_db, supplement_db, output_db)

if __name__ == "__main__":
    main()
