"""
Transfermarkt Scraper Module
Scrapes squad and match data from Transfermarkt
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from tqdm import tqdm

from config import (
    TEAMS, TM_BASE_URL, TM_SQUAD_URL, TM_MATCHES_URL,
    HEADERS, REQUEST_DELAY, START_YEAR, END_YEAR, DATA_DIR
)


@dataclass
class Player:
    """Represents a football player"""
    name: str
    position: str
    nationality: str
    birth_year: Optional[int] = None
    shirt_number: Optional[int] = None
    tm_id: Optional[str] = None


@dataclass 
class SquadData:
    """Represents a team's squad for a season"""
    team: str
    season: int
    players: List[Player]


@dataclass
class MatchData:
    """Represents a match with players who participated"""
    team: str
    date: str
    season: int
    opponent: str
    competition: str
    lineup: List[str]  # Player names who played


class TransfermarktScraper:
    """Scraper for Transfermarkt website"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make a request with rate limiting and error handling"""
        try:
            time.sleep(REQUEST_DELAY)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_squad(self, team_name: str, team_config: Dict, season: int) -> Optional[SquadData]:
        """Get squad data for a specific team and season"""
        url = TM_SQUAD_URL.format(
            base=TM_BASE_URL,
            slug=team_config['tm_slug'],
            team_id=team_config['tm_id'],
            year=season
        )
        
        soup = self._make_request(url)
        if not soup:
            return None
        
        players = []
        
        # Find player rows in the squad table
        player_rows = soup.select('table.items tbody tr.odd, table.items tbody tr.even')
        
        for row in player_rows:
            try:
                # Extract player name
                name_cell = row.select_one('td.hauptlink a')
                if not name_cell:
                    continue
                name = name_cell.text.strip()
                
                # Extract player ID from URL
                player_link = name_cell.get('href', '')
                tm_id = player_link.split('/spieler/')[-1] if '/spieler/' in player_link else None
                
                # Extract position
                position_cell = row.select('td.posrela')
                position = ""
                if position_cell:
                    pos_text = position_cell[0].select_one('tr:last-child td')
                    if pos_text:
                        position = pos_text.text.strip()
                
                # Extract nationality
                nationality_img = row.select_one('td.zentriert img.flaggenrahmen')
                nationality = nationality_img.get('title', '') if nationality_img else ''
                
                # Extract shirt number
                shirt_cell = row.select_one('div.rn_nummer')
                shirt_number = None
                if shirt_cell:
                    try:
                        shirt_number = int(shirt_cell.text.strip())
                    except ValueError:
                        pass
                
                # Extract birth year
                birth_year = None
                date_cells = row.select('td.zentriert')
                for cell in date_cells:
                    text = cell.text.strip()
                    if '(' in text and ')' in text:
                        try:
                            age = int(text.split('(')[1].replace(')', '').strip())
                            birth_year = season - age
                        except (ValueError, IndexError):
                            pass
                
                player = Player(
                    name=name,
                    position=position,
                    nationality=nationality,
                    birth_year=birth_year,
                    shirt_number=shirt_number,
                    tm_id=tm_id
                )
                players.append(player)
                
            except Exception as e:
                print(f"Error parsing player row: {e}")
                continue
        
        if players:
            return SquadData(team=team_name, season=season, players=players)
        return None
    
    def get_season_matches(self, team_name: str, team_config: Dict, season: int) -> List[MatchData]:
        """Get match data with lineups for a team's season"""
        url = TM_MATCHES_URL.format(
            base=TM_BASE_URL,
            slug=team_config['tm_slug'],
            team_id=team_config['tm_id'],
            year=season
        )
        
        soup = self._make_request(url)
        if not soup:
            return []
        
        matches = []
        
        # Find match rows
        match_rows = soup.select('div.responsive-table table tbody tr')
        
        for row in match_rows:
            try:
                # Extract date
                date_cell = row.select_one('td.zentriert a')
                if not date_cell:
                    continue
                date = date_cell.text.strip()
                
                # Extract opponent
                opponent_cell = row.select_one('td.no-border-links.hauptlink a')
                opponent = opponent_cell.text.strip() if opponent_cell else "Unknown"
                
                # Extract competition
                comp_cell = row.select_one('td.zentriert img')
                competition = comp_cell.get('title', 'League') if comp_cell else 'League'
                
                match = MatchData(
                    team=team_name,
                    date=date,
                    season=season,
                    opponent=opponent,
                    competition=competition,
                    lineup=[]  # Would need separate request to get lineup
                )
                matches.append(match)
                
            except Exception as e:
                print(f"Error parsing match row: {e}")
                continue
        
        return matches


class DataCollector:
    """Main class to collect and organize football data"""
    
    def __init__(self, teams: Dict = None, start_year: int = None, end_year: int = None):
        self.teams = teams or TEAMS
        self.start_year = start_year or START_YEAR
        self.end_year = end_year or END_YEAR
        self.scraper = TransfermarktScraper()
        self.squads: Dict[str, Dict[int, SquadData]] = {}
        
        # Create data directory
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def collect_all_squads(self, use_cache: bool = True) -> None:
        """Collect squad data for all teams across all seasons"""
        cache_file = os.path.join(DATA_DIR, "squads_cache.json")
        
        # Try to load from cache
        if use_cache and os.path.exists(cache_file):
            print("Loading squad data from cache...")
            self._load_cache(cache_file)
            return
        
        print("Collecting squad data from Transfermarkt...")
        
        for team_name, team_config in tqdm(self.teams.items(), desc="Teams"):
            self.squads[team_name] = {}
            
            for season in tqdm(range(self.start_year, self.end_year + 1), 
                              desc=f"  {team_name}", leave=False):
                squad = self.scraper.get_squad(team_name, team_config, season)
                if squad:
                    self.squads[team_name][season] = squad
                    print(f"    {team_name} {season}: {len(squad.players)} players")
        
        # Save to cache
        self._save_cache(cache_file)
    
    def _save_cache(self, filepath: str) -> None:
        """Save collected data to cache file"""
        cache_data = {}
        for team, seasons in self.squads.items():
            cache_data[team] = {}
            for season, squad in seasons.items():
                cache_data[team][str(season)] = {
                    'team': squad.team,
                    'season': squad.season,
                    'players': [asdict(p) for p in squad.players]
                }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"Cache saved to {filepath}")
    
    def _load_cache(self, filepath: str) -> None:
        """Load data from cache file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        for team, seasons in cache_data.items():
            self.squads[team] = {}
            for season_str, squad_data in seasons.items():
                players = [Player(**p) for p in squad_data['players']]
                self.squads[team][int(season_str)] = SquadData(
                    team=squad_data['team'],
                    season=squad_data['season'],
                    players=players
                )
        print(f"Loaded {len(self.squads)} teams from cache")
    
    def get_all_players(self) -> Dict[str, Dict]:
        """Get a dictionary of all unique players across all teams and seasons"""
        all_players = {}
        
        for team, seasons in self.squads.items():
            for season, squad in seasons.items():
                for player in squad.players:
                    player_key = player.name
                    if player_key not in all_players:
                        all_players[player_key] = {
                            'name': player.name,
                            'positions': set(),
                            'nationalities': set(),
                            'teams': {},
                            'tm_id': player.tm_id
                        }
                    
                    all_players[player_key]['positions'].add(player.position)
                    if player.nationality:
                        all_players[player_key]['nationalities'].add(player.nationality)
                    
                    if team not in all_players[player_key]['teams']:
                        all_players[player_key]['teams'][team] = []
                    all_players[player_key]['teams'][team].append(season)
        
        # Convert sets to lists for JSON serialization
        for player_key in all_players:
            all_players[player_key]['positions'] = list(all_players[player_key]['positions'])
            all_players[player_key]['nationalities'] = list(all_players[player_key]['nationalities'])
        
        return all_players


if __name__ == "__main__":
    # Quick test
    collector = DataCollector()
    
    # Test with one team for one season
    test_team = "Liverpool"
    test_config = TEAMS[test_team]
    
    scraper = TransfermarktScraper()
    squad = scraper.get_squad(test_team, test_config, 2023)
    
    if squad:
        print(f"\n{test_team} 2023 Squad ({len(squad.players)} players):")
        for player in squad.players[:5]:
            print(f"  - {player.name} ({player.position}) - {player.nationality}")
    else:
        print("Failed to fetch squad data")
