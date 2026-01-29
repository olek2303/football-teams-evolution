"""
Demo Data Generator
Generates sample football squad data for testing when scraping is not available
Uses realistic player names and team compositions
"""

import json
import os
import random
from typing import Dict, List
from dataclasses import asdict

from config import TEAMS, START_YEAR, END_YEAR, DATA_DIR
from scraper import Player, SquadData


# Sample player pools for demo data
SAMPLE_PLAYERS = {
    "Liverpool": {
        "goalkeepers": ["Alisson Becker", "Caoimhin Kelleher", "Adrian San Miguel"],
        "defenders": ["Virgil van Dijk", "Andrew Robertson", "Trent Alexander-Arnold", 
                     "Joe Gomez", "Joel Matip", "Ibrahima Konaté", "Kostas Tsimikas",
                     "Jamie Carragher", "Sami Hyypia", "Martin Skrtel", "Daniel Agger"],
        "midfielders": ["Jordan Henderson", "Fabinho", "Thiago Alcantara", 
                       "Alexis Mac Allister", "Dominik Szoboszlai", "Harvey Elliott",
                       "Steven Gerrard", "Xabi Alonso", "James Milner", "Gini Wijnaldum"],
        "forwards": ["Mohamed Salah", "Diogo Jota", "Luis Diaz", "Darwin Nunez",
                    "Cody Gakpo", "Roberto Firmino", "Sadio Mane", "Fernando Torres",
                    "Luis Suarez", "Daniel Sturridge"]
    },
    "Bayern Munich": {
        "goalkeepers": ["Manuel Neuer", "Sven Ulreich", "Oliver Kahn"],
        "defenders": ["Joshua Kimmich", "Alphonso Davies", "Dayot Upamecano",
                     "Matthijs de Ligt", "David Alaba", "Jerome Boateng", 
                     "Philipp Lahm", "Mats Hummels", "Rafinha"],
        "midfielders": ["Jamal Musiala", "Leon Goretzka", "Thomas Muller",
                       "Serge Gnabry", "Leroy Sane", "Bastian Schweinsteiger",
                       "Arjen Robben", "Franck Ribery", "Toni Kroos"],
        "forwards": ["Harry Kane", "Robert Lewandowski", "Mario Mandzukic",
                    "Thomas Muller", "Kingsley Coman", "Eric Maxim Choupo-Moting"]
    },
    "Legia Warszawa": {
        "goalkeepers": ["Radosław Cierzniak", "Artur Boruc", "Kacper Tobiasz"],
        "defenders": ["Artur Jędrzejczyk", "Michał Pazdan", "Bartosz Bereszyński",
                     "Jakub Rzeźniczak", "Tomasz Brzyski", "Maik Nawrocki"],
        "midfielders": ["Bartosz Kapustka", "Krzysztof Mączyński", "Tomasz Jodłowiec",
                       "Ernest Muçi", "Josue", "Yuri Ribeiro", "Luquinhas"],
        "forwards": ["Marc Gual", "Blaz Kramer", "Carlitos", "Vadis Odjidja-Ofoe",
                    "Miroslav Radović", "Nemanja Nikolić"]
    },
    "AC Milan": {
        "goalkeepers": ["Mike Maignan", "Gianluigi Donnarumma", "Dida"],
        "defenders": ["Theo Hernandez", "Fikayo Tomori", "Simon Kjær",
                     "Alessandro Nesta", "Paolo Maldini", "Cafu", "Davide Calabria"],
        "midfielders": ["Sandro Tonali", "Ismael Bennacer", "Rafael Leao",
                       "Andrea Pirlo", "Gennaro Gattuso", "Clarence Seedorf",
                       "Kaka", "Brahim Diaz"],
        "forwards": ["Olivier Giroud", "Zlatan Ibrahimović", "Filippo Inzaghi",
                    "Andriy Shevchenko", "Christian Pulisic", "Samuel Chukwueze"]
    },
    "AS Roma": {
        "goalkeepers": ["Rui Patricio", "Mile Svilar", "Francesco Totti"],
        "defenders": ["Chris Smalling", "Gianluca Mancini", "Roger Ibanez",
                     "Leonardo Spinazzola", "John Arne Riise", "Cafu"],
        "midfielders": ["Lorenzo Pellegrini", "Bryan Cristante", "Nicolo Zaniolo",
                       "Daniele De Rossi", "Francesco Totti", "Paulo Dybala"],
        "forwards": ["Tammy Abraham", "Romelu Lukaku", "Gabriel Batistuta",
                    "Edin Dzeko", "Stephan El Shaarawy"]
    },
    "Real Madrid": {
        "goalkeepers": ["Thibaut Courtois", "Iker Casillas", "Keylor Navas"],
        "defenders": ["David Alaba", "Antonio Rudiger", "Dani Carvajal",
                     "Sergio Ramos", "Marcelo", "Raphael Varane", "Ferland Mendy"],
        "midfielders": ["Luka Modric", "Toni Kroos", "Jude Bellingham",
                       "Eduardo Camavinga", "Federico Valverde", "Casemiro",
                       "Zinedine Zidane", "Claude Makelele"],
        "forwards": ["Vinicius Junior", "Rodrygo", "Kylian Mbappe",
                    "Karim Benzema", "Cristiano Ronaldo", "Gareth Bale", "Raul"]
    },
    "Barcelona": {
        "goalkeepers": ["Marc-Andre ter Stegen", "Victor Valdes", "Inaki Pena"],
        "defenders": ["Ronald Araujo", "Jules Kounde", "Alejandro Balde",
                     "Gerard Pique", "Carles Puyol", "Dani Alves", "Jordi Alba"],
        "midfielders": ["Pedri", "Gavi", "Frenkie de Jong", "Sergio Busquets",
                       "Xavi Hernandez", "Andres Iniesta", "Ilkay Gundogan"],
        "forwards": ["Robert Lewandowski", "Lamine Yamal", "Raphinha",
                    "Lionel Messi", "Neymar", "Luis Suarez", "Samuel Eto'o"]
    },
    "Manchester United": {
        "goalkeepers": ["David de Gea", "Andre Onana", "Peter Schmeichel"],
        "defenders": ["Harry Maguire", "Lisandro Martinez", "Luke Shaw",
                     "Rio Ferdinand", "Nemanja Vidic", "Patrice Evra", "Gary Neville"],
        "midfielders": ["Bruno Fernandes", "Casemiro", "Christian Eriksen",
                       "Paul Scholes", "Roy Keane", "Ryan Giggs", "David Beckham"],
        "forwards": ["Marcus Rashford", "Rasmus Hojlund", "Anthony Martial",
                    "Cristiano Ronaldo", "Wayne Rooney", "Eric Cantona", "Ruud van Nistelrooy"]
    }
}

NATIONALITIES = {
    "Liverpool": "England",
    "Bayern Munich": "Germany", 
    "Legia Warszawa": "Poland",
    "AC Milan": "Italy",
    "AS Roma": "Italy",
    "Real Madrid": "Spain",
    "Barcelona": "Spain",
    "Manchester United": "England"
}


def generate_demo_squad(team_name: str, season: int) -> SquadData:
    """Generate a realistic squad for a team and season"""
    
    if team_name not in SAMPLE_PLAYERS:
        # Create generic squad
        players = []
        for i in range(25):
            players.append(Player(
                name=f"Player_{i}_{team_name}",
                position="Midfielder" if i > 10 else ("Goalkeeper" if i == 0 else "Defender"),
                nationality="Unknown",
                birth_year=random.randint(1985, 2003),
                shirt_number=i + 1
            ))
        return SquadData(team=team_name, season=season, players=players)
    
    pool = SAMPLE_PLAYERS[team_name]
    players = []
    
    # Add goalkeepers (2-3)
    gk_count = random.randint(2, 3)
    for i, gk in enumerate(random.sample(pool["goalkeepers"], min(gk_count, len(pool["goalkeepers"])))):
        players.append(Player(
            name=gk,
            position="Goalkeeper",
            nationality=NATIONALITIES.get(team_name, "Unknown"),
            birth_year=random.randint(1985, 2000),
            shirt_number=1 if i == 0 else random.randint(12, 30)
        ))
    
    # Add defenders (7-9)
    def_count = random.randint(7, 9)
    for i, defender in enumerate(random.sample(pool["defenders"], min(def_count, len(pool["defenders"])))):
        players.append(Player(
            name=defender,
            position="Defender",
            nationality=NATIONALITIES.get(team_name, "Unknown"),
            birth_year=random.randint(1988, 2002),
            shirt_number=i + 2
        ))
    
    # Add midfielders (8-10)
    mid_count = random.randint(8, 10)
    for i, mid in enumerate(random.sample(pool["midfielders"], min(mid_count, len(pool["midfielders"])))):
        players.append(Player(
            name=mid,
            position="Midfielder",
            nationality=NATIONALITIES.get(team_name, "Unknown"),
            birth_year=random.randint(1988, 2004),
            shirt_number=i + 6
        ))
    
    # Add forwards (5-7)
    fwd_count = random.randint(5, 7)
    for i, fwd in enumerate(random.sample(pool["forwards"], min(fwd_count, len(pool["forwards"])))):
        players.append(Player(
            name=fwd,
            position="Forward",
            nationality=NATIONALITIES.get(team_name, "Unknown"),
            birth_year=random.randint(1988, 2004),
            shirt_number=i + 9
        ))
    
    return SquadData(team=team_name, season=season, players=players)


def generate_demo_data(teams: Dict = None, start_year: int = None, 
                       end_year: int = None, output_file: str = None) -> Dict:
    """Generate complete demo dataset"""
    
    teams = teams or TEAMS
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    
    if output_file is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        output_file = os.path.join(DATA_DIR, "squads_cache.json")
    
    all_data = {}
    
    print(f"Generating demo data for {len(teams)} teams, {start_year}-{end_year}...")
    
    for team_name in teams.keys():
        all_data[team_name] = {}
        
        for season in range(start_year, end_year + 1):
            squad = generate_demo_squad(team_name, season)
            all_data[team_name][str(season)] = {
                'team': squad.team,
                'season': squad.season,
                'players': [asdict(p) for p in squad.players]
            }
        
        print(f"  {team_name}: {end_year - start_year + 1} seasons generated")
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nDemo data saved to {output_file}")
    
    return all_data


if __name__ == "__main__":
    generate_demo_data()
