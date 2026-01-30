# Football Teams Evolution

Network analysis and visualization of football player connections through shared match appearances.

## Overview

This project analyzes how football players connect through playing together in matches, creating weighted network graphs that reveal team dynamics, player partnerships, and evolution over time. The system ingests historical match data from multiple sources, computes player-to-player connections, and provides interactive visualization tools.

## Features

- **Multi-Source Data Ingestion**: Scrape and store match data from StatsBomb and Footballia
- **Flexible Graph Building**: Generate player networks with extensive filtering options
- **Interactive Dashboard**: Streamlit web interface for data exploration and analysis
- **GraphStream Visualization**: 3D interactive graph rendering with Java/GraphStream
- **Historical Coverage**: Support for matches from 1990s onwards (Footballia)
- **Advanced Filtering**: By competition, position, nationality, minutes played, and more

## Architecture

### Packages

- **`packages/ft_ingest`**: Data ingestion package
  - CLI tool for scraping match data from multiple providers
  - SQLite database with match, team, player, and appearance data
  - Support for StatsBomb Open Data and Footballia archives
  
- **`packages/ft_graph`**: Graph building and export
  - Compute weighted edges between players based on shared matches
  - Export to GraphStream DGS format
  - Flexible filtering (competitions, positions, nationalities, etc.)

### Applications

- **`apps/dashboard`**: Streamlit web dashboard
  - Browse matches and lineups
  - Apply filters and build graphs interactively
  - Launch GraphStream visualizer directly from UI

### Java Components

- **`java/graph-runner`**: GraphStream visualization
  - Maven-based Java project
  - Interactive 3D graph rendering
  - Reads DGS files exported by ft_graph

## Quick Start

### 1. Installation

Clone the repository and install packages:

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install packages
pip install -e packages/ft_ingest
pip install -e packages/ft_graph
pip install -e apps/dashboard
```

### 2. Ingest Data

Scrape match data using Footballia provider:

```bash
# From pre-scraped links file
ft-ingest --db data/db/football.sqlite3 \
  --date-from 1990-01-01 \
  --date-to 2022-12-31 \
  --links-file data/fc-barcelona_match_links.txt \
  --provider footballia

# Or from team search
ft-ingest --db data/db/football.sqlite3 \
  --date-from 2010-01-01 \
  --date-to 2015-12-31 \
  --team "FC Barcelona" \
  --provider footballia
```

Or use StatsBomb Open Data:

```bash
ft-ingest --db data/db/football.sqlite3 \
  --date-from 2020-01-01 \
  --date-to 2023-12-31 \
  --team "Barcelona" \
  --provider statsbomb
```

### 3. Launch Dashboard

```bash
streamlit run apps/dashboard/src/football_dashboard/app.py
```

Navigate to http://localhost:8501 and explore the data!

### 4. Build and Visualize Graphs

Use the dashboard to:
1. Filter matches by team, date, competition
2. Apply advanced filters (positions, nationalities, min minutes)
3. Export to DGS format
4. Launch GraphStream visualizer

## Usage Examples

### Example 1: Barcelona Golden Era (2008-2012)

```bash
# Ingest Barcelona matches
ft-ingest --db barcelona.sqlite3 \
  --date-from 2008-01-01 \
  --date-to 2012-12-31 \
  --team "FC Barcelona" \
  --provider footballia

# Launch dashboard
streamlit run apps/dashboard/src/football_dashboard/app.py
```

In the dashboard:
- Select "FC Barcelona"
- Set years: 2008-2012
- Advanced filters:
  - Min shared matches: 10
  - Starters only: ✓
  - Teammates only: ✓
- Click "Render graph" to visualize

### Example 2: International Connections

```python
from sqlite3 import connect
from ft_graph.build import compute_edges
from ft_graph.dgs import export_dgs

con = connect("data/db/football.sqlite3")

edges = compute_edges(
    con,
    nationalities=["Brazil", "Argentina", "Spain"],
    min_edge_weight=5,
    same_team_only=False,  # Include opponents
)

export_dgs(con, edges, "international.dgs")
```

### Example 3: Midfield Networks

```python
edges = compute_edges(
    con,
    positions=["Midfielder", "Defensive Midfielder"],
    min_minutes=60,
    min_edge_weight=3,
    competitions=["La Liga", "Champions League"],
)

export_dgs(con, edges, "midfield.dgs")
```

## Project Structure

```
football-evolution/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── ruff.toml                         # Linting configuration
│
├── packages/                         # Python packages
│   ├── ft_ingest/                   # Data ingestion
│   │   ├── README.md
│   │   ├── pyproject.toml
│   │   └── src/ft_ingest/
│   │       ├── cli.py               # CLI entry point
│   │       ├── db.py                # Database utilities
│   │       ├── schema.sql           # Database schema
│   │       └── providers/           # Data providers
│   │           ├── base.py          # DTOs and Protocol
│   │           ├── statsbomb_open_data.py
│   │           └── footballia.py    # Footballia scraper
│   │
│   └── ft_graph/                    # Graph building
│       ├── README.md
│       ├── pyproject.toml
│       └── src/ft_graph/
│           ├── build.py             # Edge computation
│           ├── dgs.py               # DGS export
│           └── cli.py               # CLI entry point
│
├── apps/                            # Applications
│   └── dashboard/                   # Streamlit dashboard
│       ├── README.md
│       ├── pyproject.toml
│       └── src/football_dashboard/
│           └── app.py               # Main dashboard
│
├── java/                            # Java components
│   └── graph-runner/                # GraphStream viewer
│       ├── pom.xml                  # Maven configuration
│       └── src/main/java/...        # Java source
│
├── data/                            # Data files
│   ├── db/                          # SQLite databases
│   ├── exports/                     # Exported DGS files
│   ├── files/                       # Example data
│   └── raw_cache/                   # Scraping cache
│
├── scripts/                         # Helper scripts
│   ├── populate_mock_data.py
│   └── run_graph_runner.py          # Launch Java viewer
│
└── docs/                            # Documentation
```

## Database Schema

### Tables

**`team`**
- `id`: Primary key
- `name`: Team name
- `country`: Team country
- `source`: Data provider (statsbomb/footballia)
- `source_team_id`: Provider's team ID

**`player`**
- `id`: Primary key
- `name`: Player name
- `birth_date`: Date of birth
- `nationality`: Player nationality
- `source`: Data provider
- `source_player_id`: Provider's player ID

**`match`**
- `id`: Primary key
- `match_date`: Match date (YYYY-MM-DD)
- `season`: Season identifier
- `competition`: Competition name
- `home_team_id`: Home team (FK to team)
- `away_team_id`: Away team (FK to team)
- `source`: Data provider
- `source_match_id`: Provider's match ID

**`appearance`**
- `id`: Primary key
- `match_id`: FK to match
- `player_id`: FK to player
- `team_id`: FK to team
- `is_starter`: Boolean (1/0)
- `minutes`: Minutes played
- `position`: Player position

## Data Sources

### StatsBomb Open Data
- **Coverage**: Selected competitions (free tier)
- **Quality**: High (detailed event data)
- **Website**: [StatsBomb Open Data](https://github.com/statsbomb/open-data)

### Footballia
- **Coverage**: Extensive historical archive (1990s onwards)
- **Quality**: Basic (lineups only)
- **Website**: [footballia.eu](https://footballia.eu)

## Requirements

### Python
- Python 3.11+
- httpx
- beautifulsoup4
- structlog
- streamlit
- pandas

### Java (for GraphStream visualization)
- Java 11+
- Maven 3.6+

## Development

### Setup Development Environment

```bash
# Clone repository
git clone <repo-url>
cd football-evolution

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install in editable mode
pip install -e packages/ft_ingest
pip install -e packages/ft_graph
pip install -e apps/dashboard

# Install development tools
pip install ruff pytest
```

### Running Tests

```bash
# Run linting
ruff check .

# Format code
ruff format .
```

### Adding a New Data Provider

1. Create provider in `packages/ft_ingest/src/ft_ingest/providers/`
2. Implement `Provider` protocol (see `base.py`)
3. Add to `__init__.py`
4. Update CLI in `cli.py`
5. Document in provider README

## Performance Notes

- **Ingestion**: ~5 workers for parallel scraping, 1-2.5s delays between requests
- **Database**: SQLite with WAL mode for concurrent reads/writes
- **Graph Building**: Optimized SQL queries, processes 100k+ matches in seconds
- **Visualization**: GraphStream handles 1000s of nodes/edges interactively

## Team Members
- Alicja Bijak
- Patryk Pyrkosz
- Rafał Maciejewski
- Szymon Stachura
- Aleksander Karpiuk - maintaining repository

## License

See LICENSE file for details.

## Acknowledgments

- [Footballia](https://footballia.eu) for historical match archives
- [GraphStream](http://graphstream-project.org/) for visualization framework