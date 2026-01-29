"""
Graph Processor Module
Generates player co-occurrence graphs based on squad data
"""

import os
import json
from collections import defaultdict
from typing import Dict, List, Tuple, Set
from itertools import combinations
import networkx as nx
import matplotlib.pyplot as plt

from config import OUTPUT_DIR, GRAPH_DIR, DATA_DIR
from scraper import DataCollector, SquadData


class GraphProcessor:
    """Processes squad data into player co-occurrence graphs"""
    
    def __init__(self, squads: Dict[str, Dict[int, SquadData]] = None):
        self.squads = squads or {}
        
        # Co-occurrence data: {(player1, player2): {team: {season: count}}}
        self.co_occurrences: Dict[Tuple[str, str], Dict[str, Dict[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        
        # Player metadata
        self.player_info: Dict[str, Dict] = {}
        
        # Create output directories
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(GRAPH_DIR, exist_ok=True)
    
    def process_co_occurrences(self) -> None:
        """Process all squads to compute player co-occurrences"""
        print("Processing player co-occurrences...")
        
        for team, seasons in self.squads.items():
            for season, squad in seasons.items():
                player_names = [p.name for p in squad.players]
                
                # Store player info
                for player in squad.players:
                    if player.name not in self.player_info:
                        self.player_info[player.name] = {
                            'positions': set(),
                            'nationalities': set(),
                            'teams': set()
                        }
                    self.player_info[player.name]['positions'].add(player.position)
                    if player.nationality:
                        self.player_info[player.name]['nationalities'].add(player.nationality)
                    self.player_info[player.name]['teams'].add(team)
                
                # All pairs of players in the same squad played together
                for p1, p2 in combinations(sorted(player_names), 2):
                    # Ensure consistent ordering
                    pair = tuple(sorted([p1, p2]))
                    self.co_occurrences[pair][team][season] += 1
        
        print(f"Found {len(self.co_occurrences)} player pairs")
        print(f"Total unique players: {len(self.player_info)}")
    
    def generate_edge_list(self, output_file: str = None, 
                          min_seasons: int = 1) -> List[Dict]:
        """
        Generate edge list for graph visualization
        
        Output format per line: year team_name player1 player2 weight
        where weight is the number of seasons they played together
        """
        if output_file is None:
            output_file = os.path.join(OUTPUT_DIR, "player_edges.txt")
        
        edges = []
        edge_lines = []
        
        for (p1, p2), team_data in self.co_occurrences.items():
            for team, season_data in team_data.items():
                for season, count in season_data.items():
                    if count >= min_seasons:
                        edge = {
                            'year': season,
                            'team': team,
                            'player1': p1,
                            'player2': p2,
                            'weight': count
                        }
                        edges.append(edge)
                        
                        # Format for text file: year player1 player2 weight team
                        edge_lines.append(
                            f"{season}\t{p1}\t{p2}\t{count}\t{team}"
                        )
        
        # Sort by year
        edge_lines.sort()
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Format: year\tplayer1\tplayer2\tweight\tteam\n")
            for line in edge_lines:
                f.write(line + "\n")
        
        print(f"Edge list saved to {output_file} ({len(edges)} edges)")
        return edges
    
    def generate_yearly_graphs(self, output_dir: str = None) -> Dict[int, str]:
        """Generate separate graph files for each year"""
        if output_dir is None:
            output_dir = GRAPH_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Group edges by year
        yearly_edges = defaultdict(list)
        
        for (p1, p2), team_data in self.co_occurrences.items():
            for team, season_data in team_data.items():
                for season, count in season_data.items():
                    yearly_edges[season].append({
                        'player1': p1,
                        'player2': p2,
                        'weight': count,
                        'team': team
                    })
        
        output_files = {}
        
        for year in sorted(yearly_edges.keys()):
            filename = os.path.join(output_dir, f"graph_{year}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Player co-occurrence graph for {year}\n")
                f.write("# Format: player1\tplayer2\tweight\tteam\n")
                
                for edge in yearly_edges[year]:
                    f.write(f"{edge['player1']}\t{edge['player2']}\t{edge['weight']}\t{edge['team']}\n")
            
            output_files[year] = filename
        
        print(f"Generated {len(output_files)} yearly graph files")
        return output_files
    
    def generate_team_graphs(self, output_dir: str = None) -> Dict[str, str]:
        """Generate separate graph files for each team"""
        if output_dir is None:
            output_dir = GRAPH_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Group edges by team
        team_edges = defaultdict(list)
        
        for (p1, p2), team_data in self.co_occurrences.items():
            for team, season_data in team_data.items():
                total_weight = sum(season_data.values())
                seasons_together = list(season_data.keys())
                
                team_edges[team].append({
                    'player1': p1,
                    'player2': p2,
                    'total_weight': total_weight,
                    'seasons': seasons_together
                })
        
        output_files = {}
        
        for team in sorted(team_edges.keys()):
            safe_name = team.replace(' ', '_').replace('.', '')
            filename = os.path.join(output_dir, f"graph_{safe_name}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Player co-occurrence graph for {team}\n")
                f.write("# Format: player1\tplayer2\ttotal_weight\tseasons\n")
                
                for edge in team_edges[team]:
                    seasons_str = ','.join(map(str, sorted(edge['seasons'])))
                    f.write(f"{edge['player1']}\t{edge['player2']}\t{edge['total_weight']}\t[{seasons_str}]\n")
            
            output_files[team] = filename
        
        print(f"Generated {len(output_files)} team graph files")
        return output_files
    
    def generate_graphstream_format(self, output_file: str = None) -> str:
        """
        Generate graph in DGS (Dynamic Graph Stream) format for GraphStream
        """
        if output_file is None:
            output_file = os.path.join(OUTPUT_DIR, "football_graph.dgs")
        
        # Collect all years
        all_years = set()
        for team_data in self.co_occurrences.values():
            for season_data in team_data.values():
                all_years.update(season_data.keys())
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("DGS004\n")
            f.write("football_teams 0 0\n")
            
            # First add all nodes (players)
            for player_name, info in self.player_info.items():
                safe_name = player_name.replace('"', '\\"').replace(' ', '_')
                positions = list(info['positions'])
                teams = list(info['teams'])
                
                f.write(f'an "{safe_name}" ')
                f.write(f'label="{player_name}" ')
                if positions:
                    f.write(f'position="{positions[0]}" ')
                if teams:
                    f.write(f'team="{teams[0]}"\n')
            
            # Add edges grouped by year
            edge_id = 0
            for year in sorted(all_years):
                f.write(f"st {year}\n")
                
                for (p1, p2), team_data in self.co_occurrences.items():
                    for team, season_data in team_data.items():
                        if year in season_data:
                            safe_p1 = p1.replace('"', '\\"').replace(' ', '_')
                            safe_p2 = p2.replace('"', '\\"').replace(' ', '_')
                            weight = season_data[year]
                            
                            f.write(f'ae "e{edge_id}" "{safe_p1}" "{safe_p2}" ')
                            f.write(f'weight={weight} team="{team}"\n')
                            edge_id += 1
        
        print(f"GraphStream DGS file saved to {output_file}")
        return output_file
    
    def generate_gexf_format(self, output_file: str = None) -> str:
        """Generate graph in GEXF format for Gephi/GraphStream"""
        if output_file is None:
            output_file = os.path.join(OUTPUT_DIR, "football_graph.gexf")
        
        # Build NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for player_name, info in self.player_info.items():
            G.add_node(player_name,
                      positions=','.join(info['positions']),
                      teams=','.join(info['teams']))
        
        # Add edges with aggregated weights
        edge_weights = defaultdict(int)
        edge_teams = defaultdict(set)
        
        for (p1, p2), team_data in self.co_occurrences.items():
            for team, season_data in team_data.items():
                total_weight = sum(season_data.values())
                edge_weights[(p1, p2)] += total_weight
                edge_teams[(p1, p2)].add(team)
        
        for (p1, p2), weight in edge_weights.items():
            teams = ','.join(edge_teams[(p1, p2)])
            G.add_edge(p1, p2, weight=weight, teams=teams)
        
        # Write to GEXF
        nx.write_gexf(G, output_file)
        print(f"GEXF file saved to {output_file}")
        return output_file
    
    def visualize_team_graph(self, team_name: str, output_file: str = None,
                            figsize: Tuple[int, int] = (16, 12)) -> str:
        """Visualize a team's player network"""
        if output_file is None:
            safe_name = team_name.replace(' ', '_')
            output_file = os.path.join(GRAPH_DIR, f"visualization_{safe_name}.png")
        
        # Build graph for this team
        G = nx.Graph()
        
        for (p1, p2), team_data in self.co_occurrences.items():
            if team_name in team_data:
                weight = sum(team_data[team_name].values())
                G.add_edge(p1, p2, weight=weight)
        
        if len(G.nodes()) == 0:
            print(f"No data for team {team_name}")
            return None
        
        # Create visualization
        plt.figure(figsize=figsize)
        
        # Node sizes based on degree
        node_sizes = [100 + 50 * G.degree(node) for node in G.nodes()]
        
        # Edge widths based on weight
        edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
        max_weight = max(edge_weights) if edge_weights else 1
        edge_widths = [0.5 + 2 * (w / max_weight) for w in edge_weights]
        
        # Layout
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # Draw
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.3, edge_color='gray')
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='lightblue',
                               edgecolors='darkblue', linewidths=1)
        
        # Labels for high-degree nodes only
        high_degree_nodes = {node for node in G.nodes() if G.degree(node) >= 5}
        labels = {node: node.split()[-1] for node in high_degree_nodes}  # Use last name
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
        
        plt.title(f"Player Network: {team_name}")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Visualization saved to {output_file}")
        return output_file
    
    def generate_statistics(self, output_file: str = None) -> Dict:
        """Generate statistics about the player network"""
        if output_file is None:
            output_file = os.path.join(OUTPUT_DIR, "statistics.json")
        
        stats = {
            'total_players': len(self.player_info),
            'total_edges': len(self.co_occurrences),
            'teams': {},
            'top_connected_players': [],
            'top_partnerships': []
        }
        
        # Team statistics
        for team, seasons in self.squads.items():
            team_players = set()
            for season, squad in seasons.items():
                for player in squad.players:
                    team_players.add(player.name)
            
            stats['teams'][team] = {
                'unique_players': len(team_players),
                'seasons': len(seasons),
                'avg_squad_size': sum(len(s.players) for s in seasons.values()) / len(seasons) if seasons else 0
            }
        
        # Player connectivity (degree)
        player_connections = defaultdict(int)
        for (p1, p2) in self.co_occurrences.keys():
            player_connections[p1] += 1
            player_connections[p2] += 1
        
        top_players = sorted(player_connections.items(), key=lambda x: x[1], reverse=True)[:20]
        stats['top_connected_players'] = [
            {'name': name, 'connections': count}
            for name, count in top_players
        ]
        
        # Top partnerships (highest weights)
        partnership_weights = []
        for (p1, p2), team_data in self.co_occurrences.items():
            total_weight = sum(
                sum(season_data.values())
                for season_data in team_data.values()
            )
            partnership_weights.append((p1, p2, total_weight))
        
        top_partnerships = sorted(partnership_weights, key=lambda x: x[2], reverse=True)[:20]
        stats['top_partnerships'] = [
            {'player1': p1, 'player2': p2, 'seasons_together': w}
            for p1, p2, w in top_partnerships
        ]
        
        # Save statistics
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"Statistics saved to {output_file}")
        return stats


def process_squads_to_graphs(squads: Dict[str, Dict[int, SquadData]]) -> GraphProcessor:
    """Main function to process squads and generate all graph outputs"""
    processor = GraphProcessor(squads)
    processor.process_co_occurrences()
    
    # Generate various output formats
    processor.generate_edge_list()
    processor.generate_yearly_graphs()
    processor.generate_team_graphs()
    processor.generate_graphstream_format()
    processor.generate_gexf_format()
    
    # Generate statistics
    processor.generate_statistics()
    
    return processor


if __name__ == "__main__":
    # Test with sample data
    print("Testing graph processor with sample data...")
    
    from scraper import DataCollector
    
    collector = DataCollector()
    collector.collect_all_squads(use_cache=True)
    
    if collector.squads:
        processor = process_squads_to_graphs(collector.squads)
        
        # Visualize first team
        first_team = list(collector.squads.keys())[0]
        processor.visualize_team_graph(first_team)
