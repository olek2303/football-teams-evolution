import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import streamlit as st


def _ensure_repo_packages_on_path() -> None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        pkg_src = parent / "packages" / "ft_graph" / "src"
        if pkg_src.exists():
            sys.path.insert(0, str(pkg_src))
            return


_ensure_repo_packages_on_path()

from ft_graph.build import compute_edges
from ft_graph.dgs import export_dgs

st.set_page_config(page_title="Football Evolution", layout="wide")


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "scripts" / "run_graph_runner.py").exists():
            return parent
    return current.parents[5]


db_path = st.sidebar.text_input("SQLite DB path", "data/db/football.sqlite3")

if not Path(db_path).exists():
    st.warning("DB not found yet. Run ingest first.")
    st.stop()

con = sqlite3.connect(db_path)

st.title("Football teams evolution — data browser")

# Filters
teams = [r[0] for r in con.execute("SELECT name FROM team ORDER BY name").fetchall()]
select_all_teams = st.sidebar.checkbox("Select all teams", value=False)
selected_teams = st.sidebar.multiselect("Teams", teams, default=teams if select_all_teams else [])

years = [
    r[0][:4]
    for r in con.execute("SELECT DISTINCT substr(match_date,1,4) FROM match ORDER BY 1").fetchall()
    if r[0]
]
year_from = st.sidebar.selectbox("From year", years, index=0 if years else 0)
year_to = st.sidebar.selectbox("To year", years, index=(len(years) - 1) if years else 0)

# Advanced connection filters
positions_all = [
    r[0]
    for r in con.execute(
        "SELECT DISTINCT position FROM appearance WHERE position IS NOT NULL AND position != '' ORDER BY position"
    ).fetchall()
]
nationalities_all = [
    r[0]
    for r in con.execute(
        "SELECT DISTINCT nationality FROM player WHERE nationality IS NOT NULL AND nationality != '' ORDER BY nationality"
    ).fetchall()
]
competitions_all = [
    r[0]
    for r in con.execute(
        "SELECT DISTINCT competition FROM match WHERE competition IS NOT NULL AND competition != '' ORDER BY competition"
    ).fetchall()
]

with st.sidebar.expander("Advanced connection filters", expanded=False):
    min_edge_weight = st.number_input("Min shared matches", min_value=1, value=1, step=1)
    min_minutes = st.number_input("Min minutes played", min_value=0, value=0, step=5)
    starters_only = st.checkbox("Starters only", value=False)
    same_team_only = st.checkbox("Teammates only (exclude opponents)", value=False)
    competitions_filter = st.multiselect("Leagues", options=competitions_all, default=[])
    positions_filter = st.multiselect("Positions", options=positions_all, default=[])
    nationalities_filter = st.multiselect("Nationalities", options=nationalities_all, default=[])
    name_query = st.text_input("Player name contains", value="")

# Simple stats
c1, c2, c3 = st.columns(3)
c1.metric("Teams", con.execute("SELECT COUNT(*) FROM team").fetchone()[0])
c2.metric("Players", con.execute("SELECT COUNT(*) FROM player").fetchone()[0])
c3.metric("Matches", con.execute("SELECT COUNT(*) FROM match").fetchone()[0])

# Matches table
where = []
params = []
if selected_teams:
    team_placeholders = ",".join(["?"] * len(selected_teams))
    where.append(f"(t1.name IN ({team_placeholders}) OR t2.name IN ({team_placeholders}))")
    params += selected_teams + selected_teams
where.append("substr(m.match_date,1,4) BETWEEN ? AND ?")
params += [year_from, year_to]

if competitions_filter:
    where.append(f"m.competition IN ({','.join(['?'] * len(competitions_filter))})")
    params.extend(competitions_filter)

appearance_where = []
appearance_params = []
if min_minutes > 0:
    appearance_where.append("a.minutes >= ?")
    appearance_params.append(int(min_minutes))
if starters_only:
    appearance_where.append("a.is_starter = 1")
if positions_filter:
    appearance_where.append(f"a.position IN ({','.join(['?'] * len(positions_filter))})")
    appearance_params.extend(positions_filter)
if nationalities_filter:
    appearance_where.append(f"p.nationality IN ({','.join(['?'] * len(nationalities_filter))})")
    appearance_params.extend(nationalities_filter)
if name_query.strip():
    appearance_where.append("p.name LIKE ?")
    appearance_params.append(f"%{name_query.strip()}%")

if appearance_where:
    where.append(
        "EXISTS ("
        "SELECT 1 FROM appearance a "
        "JOIN player p ON p.id = a.player_id "
        "WHERE a.match_id = m.id AND " + " AND ".join(appearance_where) + ")"
    )
    params.extend(appearance_params)

wsql = " AND ".join(where)

# Count total matches for pagination
count_q = f"""
SELECT COUNT(*)
FROM match m
LEFT JOIN team t1 ON t1.id = m.home_team_id
LEFT JOIN team t2 ON t2.id = m.away_team_id
WHERE {wsql}
"""
total_matches = con.execute(count_q, params).fetchone()[0]

# Get all match IDs for graph export (without pagination)
match_ids_q = f"""
SELECT m.id
FROM match m
LEFT JOIN team t1 ON t1.id = m.home_team_id
LEFT JOIN team t2 ON t2.id = m.away_team_id
WHERE {wsql}
ORDER BY m.match_date
"""
match_ids = [r[0] for r in con.execute(match_ids_q, params).fetchall()]

# Determine if filters are active
filters_active = (
    selected_teams
    or competitions_filter
    or min_minutes > 0
    or starters_only
    or positions_filter
    or nationalities_filter
    or name_query.strip()
)

# Reset pagination when filters change
filter_key = f"{selected_teams}_{year_from}_{year_to}_{competitions_filter}_{min_minutes}_{starters_only}_{positions_filter}_{nationalities_filter}_{name_query}"
if "last_filter_key" not in st.session_state:
    st.session_state.last_filter_key = filter_key
elif st.session_state.last_filter_key != filter_key:
    st.session_state.page_num = 1
    st.session_state.last_filter_key = filter_key

# Pagination controls
heading = "Filtered Matches" if filters_active else "Matches"
st.subheader(f"{heading} ({total_matches} total)")

if total_matches == 0:
    st.info("No matches for current filters.")
else:
    # Pagination settings
    matches_per_page = st.sidebar.number_input(
        "Matches per page", min_value=5, max_value=50, value=10, step=5
    )
    total_pages = (total_matches + matches_per_page - 1) // matches_per_page

    # Initialize page number in session state
    if "page_num" not in st.session_state:
        st.session_state.page_num = 1

    # Fetch paginated matches
    offset = (st.session_state.page_num - 1) * matches_per_page
    q = f"""
    SELECT m.id, m.match_date, t1.name, t2.name, m.competition
    FROM match m
    LEFT JOIN team t1 ON t1.id = m.home_team_id
    LEFT JOIN team t2 ON t2.id = m.away_team_id
    WHERE {wsql}
    ORDER BY m.match_date
    LIMIT ? OFFSET ?
    """
    rows = con.execute(q, params + [matches_per_page, offset]).fetchall()

    player_filters_sql = []
    player_filters_params: list = []
    if min_minutes > 0:
        player_filters_sql.append("a.minutes >= ?")
        player_filters_params.append(int(min_minutes))
    if starters_only:
        player_filters_sql.append("a.is_starter = 1")
    if positions_filter:
        player_filters_sql.append(f"a.position IN ({','.join(['?'] * len(positions_filter))})")
        player_filters_params.extend(positions_filter)
    if nationalities_filter:
        player_filters_sql.append(
            f"p.nationality IN ({','.join(['?'] * len(nationalities_filter))})"
        )
        player_filters_params.extend(nationalities_filter)
    if name_query.strip():
        player_filters_sql.append("p.name LIKE ?")
        player_filters_params.append(f"%{name_query.strip()}%")

    players_where_sql = " AND ".join(["a.match_id = ?"] + player_filters_sql)

    for match_id, match_date, home_team, away_team, competition in rows:
        title = f"{match_date} • {home_team} vs {away_team} • {competition}"
        with st.expander(title, expanded=False):
            psql = f"""
            SELECT p.name,
                   t.name AS team,
                   a.position,
                   a.minutes,
                   a.is_starter,
                   p.nationality
            FROM appearance a
            JOIN player p ON p.id = a.player_id
            JOIN team t ON t.id = a.team_id
            WHERE {players_where_sql}
            ORDER BY t.name, a.is_starter DESC, a.minutes DESC, p.name
            """
            pparams = [match_id] + player_filters_params
            prow = con.execute(psql, pparams).fetchall()

            if not prow:
                st.caption("No players match the current filters for this match.")
            else:
                import pandas as pd

                df = pd.DataFrame(
                    prow,
                    columns=["Player", "Team", "Position", "Minutes", "Starter", "Nationality"],
                )
                st.dataframe(df, use_container_width=True)

    # Pagination controls at the bottom
    st.divider()

    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        st.caption(
            f"Showing {offset + 1}-{min(offset + matches_per_page, total_matches)} of {total_matches}"
        )

    with col2:
        # Center navigation buttons
        nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 1, 1])

        with nav_col1:
            if st.button(
                "⏮️",
                key="first",
                help="First page",
                disabled=st.session_state.page_num == 1,
                use_container_width=True,
            ):
                st.session_state.page_num = 1
                st.rerun()

        with nav_col2:
            if st.button(
                "◀️",
                key="prev",
                help="Previous page",
                disabled=st.session_state.page_num == 1,
                use_container_width=True,
            ):
                st.session_state.page_num -= 1
                st.rerun()

        with nav_col3:
            st.markdown(
                f"<div style='text-align: center; padding: 8px;'><b>Page {st.session_state.page_num} of {total_pages}</b></div>",
                unsafe_allow_html=True,
            )

        with nav_col4:
            if st.button(
                "▶️",
                key="next",
                help="Next page",
                disabled=st.session_state.page_num == total_pages,
                use_container_width=True,
            ):
                st.session_state.page_num += 1
                st.rerun()

        with nav_col5:
            if st.button(
                "⏭️",
                key="last",
                help="Last page",
                disabled=st.session_state.page_num == total_pages,
                use_container_width=True,
            ):
                st.session_state.page_num = total_pages
                st.rerun()

st.subheader("Export selection to GraphStream DGS")
if selected_teams:
    team_name = "_".join(
        [t.replace(" ", "_") for t in selected_teams[:3]]
    )  # Use up to 3 team names
    if len(selected_teams) > 3:
        team_name += f"_plus{len(selected_teams) - 3}"
    default_name = f"data/exports/{team_name}_{year_from}_{year_to}.dgs"
else:
    default_name = f"data/exports/all_{year_from}_{year_to}.dgs"
out_name = st.text_input("Output file", default_name)

if st.button("Build edges + Export .dgs"):
    edges = compute_edges(
        con,
        match_ids=match_ids if match_ids else None,
        competitions=competitions_filter or None,
        min_edge_weight=int(min_edge_weight),
        min_minutes=int(min_minutes) if min_minutes > 0 else None,
        starters_only=starters_only,
        positions=positions_filter or None,
        nationalities=nationalities_filter or None,
        name_query=name_query.strip() or None,
        same_team_only=same_team_only,
    )
    export_dgs(con, edges, out_name, graph_name="players")
    st.success(f"Exported: {out_name} (edges: {len(edges)})")

if st.button("Render graph"):
    repo_root = _find_repo_root()
    dgs_path = Path(out_name)
    if not dgs_path.is_absolute():
        dgs_path = (repo_root / dgs_path).resolve()

    try:
        with st.spinner("Exporting graph for selected params..."):
            edges = compute_edges(
                con,
                match_ids=match_ids if match_ids else None,
                competitions=competitions_filter or None,
                min_edge_weight=int(min_edge_weight),
                min_minutes=int(min_minutes) if min_minutes > 0 else None,
                starters_only=starters_only,
                positions=positions_filter or None,
                nationalities=nationalities_filter or None,
                name_query=name_query.strip() or None,
                same_team_only=same_team_only,
            )
            export_dgs(con, edges, str(dgs_path), graph_name="players")
            st.success(f"Exported: {dgs_path} (edges: {len(edges)})")

        with st.spinner("Launching GraphStream viewer..."):
            cmd = [
                sys.executable,
                str(repo_root / "scripts" / "run_graph_runner.py"),
                str(dgs_path),
            ]
            proc = subprocess.Popen(
                cmd,
                cwd=str(repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(1)
            if proc.poll() is not None and proc.returncode != 0:
                out, err = proc.communicate(timeout=2)
                st.error("❌ Something went wrong while launching the graph viewer!")
                st.error("Possible causes:")
                if proc.returncode == 2:
                    st.error(
                        "• The graph runner could not load the .dgs file (path may be incorrect or inaccessible)"
                    )
                    st.caption(f"DGS path passed to graph runner: {dgs_path}")
                elif proc.returncode == 3:
                    st.error("• Maven is not installed or not in PATH")
                else:
                    st.error(f"• Exit code: {proc.returncode}")
                if err:
                    st.text_area("Error details:", err, height=150, disabled=True)
                if out:
                    st.text_area("Output:", out, height=100, disabled=True)
            else:
                # Close unused pipes to avoid leaking stdout/stderr resources
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
                st.success("Graph runner launched. The viewer window should appear.")
                st.caption("If nothing opens, ensure Maven/Java are installed and try again.")
    except Exception as e:
        st.error("❌ Something went wrong!")
        st.error(f"Error: {e!s}")
        st.text_area("Details:", f"{type(e).__name__}: {e!s}", height=100, disabled=True)
