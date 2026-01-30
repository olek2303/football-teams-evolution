"""
Script to ingest data for multiple teams from Footballia.

This script runs ft-ingest for a list of teams, one at a time,
to avoid overwhelming the source website with parallel requests.
"""

import subprocess
import sys
from pathlib import Path

# List of teams to ingest
TEAMS = [
    "Real Madrid",
    "Manchester United",
    "Liverpool",
    "Bayern Munich",
    "Juventus",
    "Inter Milan",
    "Arsenal",
    "Chelsea",
    "Paris Saint-Germain",
    "Borussia Dortmund",
    "Atletico Madrid",
    "Ajax",
    "Benfica",
    "Porto",
    "Celtic",
    "Rangers",
    "AC Milan",
    "Tottenham Hotspur",
    "Manchester City",
    "FC Barcelona",
    "AS Roma",
    "Napoli",
    "Lazio",
    "Sevilla",
    "Villarreal",
    "Valencia",
    "Olympique Lyonnais",
    "Marseille",
    "Galatasaray",
    "Fenerbahce",
    "Besiktas",
    "Shakhtar Donetsk",
    "Dynamo Kyiv",
    "PSV Eindhoven",
]

# Configuration
DB_PATH = "data/db/football.sqlite3"
DATE_FROM = "1990-01-01"
DATE_TO = "2026-12-31"
PROVIDER = "footballia"


def run_ingest_for_team(team_name: str) -> bool:
    """Run ft-ingest for a single team. Returns True if successful."""
    print(f"\n{'=' * 80}")
    print(f"🔄 Ingesting data for: {team_name}")
    print(f"{'=' * 80}\n")

    cmd = [
        "ft-ingest",
        "--db",
        DB_PATH,
        "--date-from",
        DATE_FROM,
        "--date-to",
        DATE_TO,
        "--team",
        team_name,
        "--provider",
        PROVIDER,
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=False,  # Show output in real-time
        )
        print(f"\n✅ Successfully ingested data for: {team_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to ingest data for: {team_name}")
        print(f"   Error code: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Stopping...")
        sys.exit(1)


def main():
    print("╔" + "=" * 78 + "╗")
    print("║" + " MULTI-TEAM DATA INGESTION ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    print("📊 Configuration:")
    print(f"   Database: {DB_PATH}")
    print(f"   Date range: {DATE_FROM} to {DATE_TO}")
    print(f"   Provider: {PROVIDER}")
    print(f"   Teams to ingest: {len(TEAMS)}")
    print()
    print("Teams:")
    for i, team in enumerate(TEAMS, 1):
        print(f"   {i:2d}. {team}")
    print()

    # Check if database path parent exists
    db_parent = Path(DB_PATH).parent
    if not db_parent.exists():
        print(f"⚠️  Warning: Database directory does not exist: {db_parent}")
        print("   Creating directory...")
        db_parent.mkdir(parents=True, exist_ok=True)

    response = input("Proceed with ingestion? (yes/no): ").strip().lower()
    if response not in ("yes", "y"):
        print("Cancelled.")
        return

    print("\n" + "=" * 80)
    print("Starting ingestion process...")
    print("=" * 80)

    successful = []
    failed = []

    for i, team in enumerate(TEAMS, 1):
        print(f"\n[{i}/{len(TEAMS)}] Processing: {team}")

        if run_ingest_for_team(team):
            successful.append(team)
        else:
            failed.append(team)

            # Ask if user wants to continue after failure
            response = input("\n⚠️  Continue with remaining teams? (yes/no): ").strip().lower()
            if response not in ("yes", "y"):
                print("Stopping ingestion process.")
                break

    # Summary
    print("\n" + "=" * 80)
    print("INGESTION SUMMARY")
    print("=" * 80)
    print(f"\n✅ Successful: {len(successful)}/{len(TEAMS)}")
    if successful:
        for team in successful:
            print(f"   ✓ {team}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(TEAMS)}")
        for team in failed:
            print(f"   ✗ {team}")

    print("\n" + "=" * 80)
    print("✨ Done!")
    print("=" * 80)


if __name__ == "__main__":
    main()
