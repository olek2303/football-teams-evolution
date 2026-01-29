#!/usr/bin/env python3
"""
Football Teams Evolution Project
================================

Main entry point for the project.
Collects squad data, processes player co-occurrences, and generates graph outputs.

Usage:
    python main.py --mode demo      # Use demo data (no scraping)
    python main.py --mode scrape    # Scrape data from Transfermarkt
    python main.py --mode cache     # Use cached data if available
    python main.py --help           # Show help
"""

import argparse
import os
import sys
import json
from typing import Dict

from config import TEAMS, START_YEAR, END_YEAR, OUTPUT_DIR, GRAPH_DIR, DATA_DIR
from scraper import DataCollector, SquadData, Player
from graph_processor import GraphProcessor, process_squads_to_graphs
from demo_data import generate_demo_data


def load_squads_from_cache(cache_file: str) -> Dict[str, Dict[int, SquadData]]:
    """Load squad data from cache file"""
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
    
    squads = {}
    for team, seasons in cache_data.items():
        squads[team] = {}
        for season_str, squad_data in seasons.items():
            players = [Player(**p) for p in squad_data['players']]
            squads[team][int(season_str)] = SquadData(
                team=squad_data['team'],
                season=squad_data['season'],
                players=players
            )
    
    return squads


def print_summary(squads: Dict[str, Dict[int, SquadData]], processor: GraphProcessor):
    """Print summary of collected data"""
    print("\n" + "="*60)
    print("DATA COLLECTION SUMMARY")
    print("="*60)
    
    total_players = set()
    total_seasons = 0
    
    for team, seasons in squads.items():
        print(f"\n{team}:")
        for season, squad in sorted(seasons.items()):
            print(f"  {season}: {len(squad.players)} players")
            for player in squad.players:
                total_players.add(player.name)
        total_seasons += len(seasons)
    
    print(f"\n{'='*60}")
    print(f"TOTALS:")
    print(f"  Teams: {len(squads)}")
    print(f"  Seasons: {total_seasons}")
    print(f"  Unique Players: {len(total_players)}")
    print(f"  Player Pairs (edges): {len(processor.co_occurrences)}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Football Teams Evolution Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode demo                    # Use demo data
  python main.py --mode scrape --teams Liverpool Bayern Munich
  python main.py --mode cache --start 2015 --end 2023
        """
    )
    
    parser.add_argument(
        '--mode', 
        choices=['demo', 'scrape', 'cache'],
        default='demo',
        help='Data collection mode: demo (generated), scrape (from web), cache (from file)'
    )
    
    parser.add_argument(
        '--teams',
        nargs='+',
        help='List of teams to process (default: all configured teams)'
    )
    
    parser.add_argument(
        '--start',
        type=int,
        default=START_YEAR,
        help=f'Start year (default: {START_YEAR})'
    )
    
    parser.add_argument(
        '--end',
        type=int,
        default=END_YEAR,
        help=f'End year (default: {END_YEAR})'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate network visualizations'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=OUTPUT_DIR,
        help=f'Output directory (default: {OUTPUT_DIR})'
    )
    
    args = parser.parse_args()
    
    # Filter teams if specified
    teams = TEAMS
    if args.teams:
        teams = {name: config for name, config in TEAMS.items() if name in args.teams}
        if not teams:
            print(f"Error: No matching teams found. Available: {list(TEAMS.keys())}")
            sys.exit(1)
    
    # Create output directories
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(GRAPH_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    cache_file = os.path.join(DATA_DIR, "squads_cache.json")
    
    print(f"\nFootball Teams Evolution Project")
    print(f"================================")
    print(f"Mode: {args.mode}")
    print(f"Teams: {list(teams.keys())}")
    print(f"Period: {args.start} - {args.end}")
    print()
    
    # Collect or load data based on mode
    squads = {}
    
    if args.mode == 'demo':
        print("Generating demo data...")
        generate_demo_data(teams, args.start, args.end, cache_file)
        squads = load_squads_from_cache(cache_file)
        
    elif args.mode == 'cache':
        if os.path.exists(cache_file):
            print(f"Loading data from cache: {cache_file}")
            squads = load_squads_from_cache(cache_file)
        else:
            print("No cache found, generating demo data...")
            generate_demo_data(teams, args.start, args.end, cache_file)
            squads = load_squads_from_cache(cache_file)
            
    elif args.mode == 'scrape':
        print("Scraping data from Transfermarkt...")
        print("NOTE: This may take a while due to rate limiting.")
        
        collector = DataCollector(teams, args.start, args.end)
        collector.collect_all_squads(use_cache=False)
        squads = collector.squads
    
    if not squads:
        print("Error: No data collected!")
        sys.exit(1)
    
    # Process data and generate graphs
    print("\nProcessing player co-occurrences...")
    processor = GraphProcessor(squads)
    processor.process_co_occurrences()
    
    # Generate outputs
    print("\nGenerating output files...")
    
    # 1. Main edge list
    edge_file = processor.generate_edge_list(
        os.path.join(args.output_dir, "player_edges.txt")
    )
    
    # 2. Yearly graphs
    processor.generate_yearly_graphs(GRAPH_DIR)
    
    # 3. Team-specific graphs
    processor.generate_team_graphs(GRAPH_DIR)
    
    # 4. GraphStream DGS format
    processor.generate_graphstream_format(
        os.path.join(args.output_dir, "football_graph.dgs")
    )
    
    # 5. GEXF format (for Gephi)
    processor.generate_gexf_format(
        os.path.join(args.output_dir, "football_graph.gexf")
    )
    
    # 6. Statistics
    stats = processor.generate_statistics(
        os.path.join(args.output_dir, "statistics.json")
    )
    
    # 7. Visualizations (optional)
    if args.visualize:
        print("\nGenerating visualizations...")
        for team in squads.keys():
            processor.visualize_team_graph(team)
    
    # Print summary
    print_summary(squads, processor)
    
    # Print output file locations
    print(f"\nOutput files created:")
    print(f"  - {args.output_dir}/player_edges.txt (main edge list)")
    print(f"  - {args.output_dir}/football_graph.dgs (GraphStream format)")
    print(f"  - {args.output_dir}/football_graph.gexf (GEXF format)")
    print(f"  - {args.output_dir}/statistics.json (statistics)")
    print(f"  - {GRAPH_DIR}/graph_*.txt (yearly and team graphs)")
    
    if args.visualize:
        print(f"  - {GRAPH_DIR}/visualization_*.png (network visualizations)")
    
    print("\n✓ Project completed successfully!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
