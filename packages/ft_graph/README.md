# ft-graph

Football player network graph builder and exporter for GraphStream visualization.

Builds weighted graphs of player connections based on shared match appearances, with configurable filtering for competitions, positions, nationalities, and more.

## Features

- **Flexible Edge Computation**: Build player networks from SQLite match database
- **Advanced Filtering**:
  - Min shared matches (edge weight)
  - Min minutes played per match
  - Starters only
  - Teammates only (exclude opponents)
  - Specific competitions
  - Player positions
  - Player nationalities
  - Player name search
- **GraphStream Export**: DGS format for interactive visualization
- **Attribute Enrichment**: Includes player/team attributes in exported graph

## Installation

From the repository root:

```bash
pip install -e packages/ft_graph
```

## Usage

### As a Library

```python
from sqlite3 import connect
from ft_graph.build import compute_edges
from ft_graph.dgs import export_dgs

# Connect to database
con = connect("football.sqlite3")

# Compute edges with filters
edges = compute_edges(
    con,
    match_ids=[1, 2, 3],  # Optional: specific match IDs
    min_edge_weight=3,     # Players must share at least 3 matches
    min_minutes=45,        # Each player must play at least 45 min/match
    starters_only=True,    # Only consider starting XI
    same_team_only=True,   # Only teammates (no opponents)
    competitions=["La Liga", "Champions League"],
    positions=["Forward", "Midfielder"],
    nationalities=["Spain", "Brazil"],
    name_query="silva",    # Filter by player name
)

# Export to DGS
export_dgs(con, edges, "output.dgs", graph_name="player_network")
```

### CLI (via ft-graph-export)

```bash
ft-graph-export --db football.sqlite3 \
  --output network.dgs \
  --min-weight 5 \
  --min-minutes 60 \
  --starters-only \
  --same-team-only
```

## API Reference

### `compute_edges()`

Compute weighted edges between players based on shared match appearances.

**Parameters**:
- `con` (Connection): SQLite database connection
- `match_ids` (list[int] | None): Filter to specific match IDs
- `competitions` (list[str] | None): Filter by competition names
- `min_edge_weight` (int): Minimum shared matches (default: 1)
- `min_minutes` (int | None): Minimum minutes played per match
- `starters_only` (bool): Only consider starting lineups (default: False)
- `positions` (list[str] | None): Filter by player positions
- `nationalities` (list[str] | None): Filter by player nationalities
- `name_query` (str | None): Filter by player name (case-insensitive)
- `same_team_only` (bool): Exclude opponent connections (default: False)

**Returns**: `list[tuple[int, int, int]]` - List of (player1_id, player2_id, weight) tuples

### `export_dgs()`

Export graph to GraphStream DGS format.

**Parameters**:
- `con` (Connection): SQLite database connection
- `edges` (list[tuple[int, int, int]]): Edge list from `compute_edges()`
- `output_path` (str): Output file path
- `graph_name` (str): Graph identifier (default: "players")

## DGS Format

The exported DGS file includes:

**Node Attributes**:
- `ui.label`: Player name
- `team`: Team name
- `nationality`: Player nationality
- `position`: Player position
- `birth_date`: Player birth date

**Edge Attributes**:
- `weight`: Number of shared matches
- `ui.label`: Weight as string

## Integration with GraphStream

The exported `.dgs` files can be visualized using:

1. **Java GraphStream Viewer** (included in this repo):
   ```bash
   python scripts/run_graph_runner.py output.dgs
   ```

2. **GraphStream Java Library**:
   ```java
   import org.graphstream.stream.file.FileSource;
   import org.graphstream.stream.file.FileSourceDGS;
   
   FileSource fs = new FileSourceDGS();
   Graph g = new DefaultGraph("player-network");
   fs.addSink(g);
   fs.readAll("output.dgs");
   ```

3. **Gephi** (via GraphStream plugin)

## Examples

### Barcelona Players Network (2010-2015)

```python
edges = compute_edges(
    con,
    competitions=["La Liga", "Champions League"],
    min_edge_weight=10,
    min_minutes=45,
    starters_only=True,
    same_team_only=True,
)
export_dgs(con, edges, "barcelona_2010_2015.dgs")
```

### International Connections

```python
edges = compute_edges(
    con,
    nationalities=["Brazil", "Argentina"],
    min_edge_weight=5,
    same_team_only=False,  # Include opponent connections
)
export_dgs(con, edges, "international_network.dgs")
```

### Midfield Network

```python
edges = compute_edges(
    con,
    positions=["Midfielder", "Defensive Midfielder"],
    min_minutes=60,
    min_edge_weight=3,
)
export_dgs(con, edges, "midfield_network.dgs")
```

## Performance

- Edge computation is optimized with SQL joins and filtering
- Large databases (100k+ matches) process in seconds
- Memory usage scales with number of unique players in filtered dataset

## Dependencies

- Python 3.11+
- Standard library only (no external dependencies)

## License

See repository root for license information.