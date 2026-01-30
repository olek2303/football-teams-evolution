# ft-ingest

Football match data ingestion package that scrapes and stores match data from multiple providers into a SQLite database.

## Features

- **Multiple Data Providers**:
  - **StatsBomb Open Data**: Free, high-quality match event data
  - **Footballia**: Historical match archive with lineups from 1990s onwards

- **Flexible CLI**: Filter by teams, date ranges, competitions, and more
- **Parallel Processing**: Optimized with ThreadPoolExecutor for fast scraping
- **Thread-Safe Database**: SQLite with WAL mode and proper locking for concurrent writes
- **Structured Logging**: Progress tracking with structlog

## Installation

From the repository root:

```bash
pip install -e packages/ft_ingest
```

## Usage

### Basic Commands

**StatsBomb Provider** (default):
```bash
ft-ingest --db football.sqlite3 \
  --date-from 2020-01-01 \
  --date-to 2023-12-31 \
  --team "Barcelona" \
  --team "Real Madrid"
```

**Footballia Provider** (from team search):
```bash
ft-ingest --db football.sqlite3 \
  --date-from 1990-01-01 \
  --date-to 2022-12-31 \
  --team "FC Barcelona" \
  --provider footballia
```

**Footballia Provider** (from pre-scraped links file):
```bash
ft-ingest --db football.sqlite3 \
  --date-from 1990-01-01 \
  --date-to 2022-12-31 \
  --links-file data/fc-barcelona_match_links.txt \
  --provider footballia
```

### CLI Arguments

- `--db`: Path to SQLite database (will be created if doesn't exist)
- `--date-from`: Start date (YYYY-MM-DD format)
- `--date-to`: End date (YYYY-MM-DD format)
- `--team`: Team name to fetch (can be specified multiple times)
- `--links-file`: Path to file with match URLs (one per line)
- `--provider`: Data provider (`statsbomb` or `footballia`, default: `statsbomb`)

## Database Schema

The database contains the following tables:

- `team`: Team information (name, country, source IDs)
- `player`: Player information (name, birth date, nationality)
- `match`: Match information (date, season, competition, teams)
- `appearance`: Player appearances in matches (position, minutes, starter status)

## Provider Details

### StatsBomb Open Data

- **Source**: Free event data from StatsBomb
- **Coverage**: Selected competitions and matches
- **Data Quality**: High (detailed event data)
- **Rate Limiting**: None (open data)

### Footballia

- **Source**: footballia.eu historical archive
- **Coverage**: Extensive historical matches from 1990s onwards
- **Data Quality**: Basic (lineups only, no detailed events)
- **Rate Limiting**: Built-in delays (1-2.5s between requests)
- **Parallel Processing**: 5 workers for metadata fetching
- **Features**:
  - Automatic date extraction from match pages
  - Competition name cleaning (removes season suffixes)
  - Paginated team search with year filtering
  - Links file support for pre-scraped match URLs

## Architecture

### Provider Protocol

All providers implement the `Provider` protocol:

```python
class Provider(Protocol):
    name: str
    
    def list_matches(self, teams: list[str], date_from: str, date_to: str) -> list[MatchDTO]:
        ...
    
    def get_lineups(self, source_match_id: str) -> list[AppearanceDTO]:
        ...
```

### DTOs (Data Transfer Objects)

- `MatchDTO`: Match metadata (date, teams, competition, season)
- `TeamDTO`: Team data (name, country, source IDs)
- `PlayerDTO`: Player data (name, birth date, nationality, source IDs)
- `AppearanceDTO`: Player appearance in match (team, position, minutes, starter)

## Development

### Adding a New Provider

1. Create a new file in `src/ft_ingest/providers/`
2. Implement the `Provider` protocol
3. Add to `src/ft_ingest/providers/__init__.py`
4. Add provider choice to CLI in `cli.py`

### Testing

```bash
# Test with small date range first
ft-ingest --db test.sqlite3 \
  --date-from 2023-01-01 \
  --date-to 2023-01-31 \
  --team "Barcelona" \
  --provider footballia
```

## Dependencies

- `httpx`: HTTP client for API requests
- `beautifulsoup4`: HTML parsing for Footballia scraper
- `structlog`: Structured logging
- Python 3.11+

## License

See repository root for license information.