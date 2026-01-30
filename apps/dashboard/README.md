# Football Evolution Dashboard

Interactive Streamlit dashboard for browsing football match data and building player network visualizations.

## Features

- **Match Browser**: Filter and explore matches by team, date, competition
- **Advanced Filters**: 
  - Min shared matches
  - Min minutes played
  - Starters only
  - Teammates only
  - Competitions
  - Player positions
  - Player nationalities
  - Player name search
- **Player Lineups**: Expandable match details with full lineups
- **Graph Export**: Export filtered data to GraphStream DGS format
- **Graph Visualization**: Launch integrated GraphStream viewer from dashboard
- **Multi-Team Selection**: Filter matches involving multiple teams

## Installation

From the repository root:

```bash
pip install -e apps/dashboard
```

## Usage

### Launch Dashboard

```bash
streamlit run apps/dashboard/src/football_dashboard/app.py
```

Or with auto-reload on save:

```bash
streamlit run apps/dashboard/src/football_dashboard/app.py --server.runOnSave true
```

### Configure Database

1. Set the SQLite database path in the sidebar (default: `data/db/football.sqlite3`)
2. If the database doesn't exist, run `ft-ingest` first (see ft-ingest package)

### Workflow

1. **Select Teams**: Choose one or more teams (or "Select all teams")
2. **Set Date Range**: Pick from/to years
3. **Apply Advanced Filters** (optional):
   - Min shared matches for edge weight
   - Min minutes played
   - Filter by competitions, positions, nationalities
   - Search by player name
4. **Browse Matches**: Expand match cards to see lineups
5. **Export Graph**: Configure output file and click "Build edges + Export .dgs"
6. **Visualize** (optional): Click "Render graph" to launch GraphStream viewer

## Interface Guide

### Sidebar

- **SQLite DB path**: Path to football database
- **Teams**: Multi-select dropdown (with "Select all" checkbox)
- **From year / To year**: Date range filters
- **Advanced connection filters** (expandable):
  - Min shared matches
  - Min minutes played
  - Starters only checkbox
  - Teammates only checkbox
  - Leagues multi-select
  - Positions multi-select
  - Nationalities multi-select
  - Player name search

### Main View

- **Metrics**: Team/Player/Match counts
- **Matches**: Expandable list (limit 500)
  - Each match shows: Date • Home vs Away • Competition
  - Expand to see lineup table with: Player, Team, Position, Minutes, Starter, Nationality
- **Export section**:
  - Output file path (auto-generated from filters)
  - "Build edges + Export .dgs" button
  - "Render graph" button (launches Java viewer)

## Graph Rendering

The dashboard integrates with the Java GraphStream viewer:

### Requirements

- Java 11+ installed
- Maven installed and in PATH
- `java/graph-runner` built (automatic via `scripts/run_graph_runner.py`)

### How It Works

1. Dashboard exports filtered data to `.dgs` file
2. Launches `scripts/run_graph_runner.py` with subprocess
3. Script compiles Maven project if needed
4. Opens interactive GraphStream window

### Troubleshooting

If graph viewer fails:

- **Exit code 2**: DGS file path is incorrect or inaccessible
- **Exit code 3**: Maven not installed or not in PATH
- Check error details in dashboard error messages

## Examples

### Barcelona Network (2008-2012)

1. Select "FC Barcelona" in Teams
2. Set From year: 2008, To year: 2012
3. Advanced filters:
   - Min shared matches: 10
   - Starters only: ✓
   - Teammates only: ✓
4. Export to: `data/exports/barcelona_golden_era.dgs`
5. Click "Render graph"

### International Rivalries

1. Select all teams checkbox
2. Set date range to full database coverage
3. Advanced filters:
   - Nationalities: Spain, Brazil, Argentina
   - Min shared matches: 5
   - Teammates only: ✗ (to include opponents)
4. Export and visualize

### Midfield Connections

1. Select multiple top teams
2. Advanced filters:
   - Positions: Midfielder, Defensive Midfielder
   - Min minutes: 60
   - Min shared matches: 3
3. Export for analysis

## Architecture

### File Structure

```
apps/dashboard/
├── pyproject.toml          # Dependencies (streamlit, pandas)
├── README.md               # This file
└── src/
    └── football_dashboard/
        └── app.py          # Main Streamlit app
```

### Dependencies

- `streamlit`: Web dashboard framework
- `pandas`: DataFrame display for lineups
- `ft_graph`: Graph building (auto-imported from repo)

### Database Queries

The app builds dynamic SQL queries with:

- Team filtering (home OR away in selected teams)
- Date range filtering (BETWEEN years)
- Competition filtering (IN clause)
- Subquery for player appearance filters (EXISTS clause)
- Ordering and limits (500 matches max)

## Performance

- **Match queries**: Fast with proper indexes (< 1s for 100k matches)
- **Graph building**: Delegates to `ft_graph.compute_edges()`
- **Graph rendering**: Subprocess launch, non-blocking
- **UI responsiveness**: Auto-refresh on save enabled by default

## Configuration

### Streamlit Settings

Set in `app.py`:

```python
st.set_page_config(page_title="Football Evolution", layout="wide")
```

### Custom Database Path

Modify default in sidebar:

```python
db_path = st.sidebar.text_input("SQLite DB path", "your/custom/path.sqlite3")
```

## Dependencies

- `streamlit>=1.30.0`
- `pandas>=2.0.0`
- `ft_graph` (local package)
- Python 3.11+

## Development

### Run with Debug

```bash
streamlit run apps/dashboard/src/football_dashboard/app.py --logger.level=debug
```

### Hot Reload

Streamlit automatically reloads on file changes when run with `--server.runOnSave true`.

## License

See repository root for license information.