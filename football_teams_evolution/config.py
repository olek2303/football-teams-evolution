"""
Configuration for Football Teams Evolution Project
Contains team definitions, URL patterns, and settings
"""

# Team configurations for Transfermarkt
# Format: (team_name, transfermarkt_id, transfermarkt_url_slug)
TEAMS = {
    "Liverpool": {
        "tm_id": 31,
        "tm_slug": "fc-liverpool",
        "country": "England",
        "league": "Premier League"
    },
    "Bayern Munich": {
        "tm_id": 27,
        "tm_slug": "fc-bayern-munchen",
        "country": "Germany",
        "league": "Bundesliga"
    },
    "Legia Warszawa": {
        "tm_id": 39,
        "tm_slug": "legia-warschau",
        "country": "Poland",
        "league": "Ekstraklasa"
    },
    "AC Milan": {
        "tm_id": 5,
        "tm_slug": "ac-mailand",
        "country": "Italy",
        "league": "Serie A"
    },
    "AS Roma": {
        "tm_id": 12,
        "tm_slug": "as-rom",
        "country": "Italy",
        "league": "Serie A"
    },
    "Real Madrid": {
        "tm_id": 418,
        "tm_slug": "real-madrid",
        "country": "Spain",
        "league": "La Liga"
    },
    "Barcelona": {
        "tm_id": 131,
        "tm_slug": "fc-barcelona",
        "country": "Spain",
        "league": "La Liga"
    },
    "Manchester United": {
        "tm_id": 985,
        "tm_slug": "manchester-united",
        "country": "England",
        "league": "Premier League"
    }
}

# Time period for data collection
START_YEAR = 2010
END_YEAR = 2024

# Transfermarkt base URLs
TM_BASE_URL = "https://www.transfermarkt.com"
TM_SQUAD_URL = "{base}/{slug}/kader/verein/{team_id}/saison_id/{year}/plus/1"
TM_MATCHES_URL = "{base}/{slug}/spielplan/verein/{team_id}/saison_id/{year}"

# Request headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# Rate limiting settings
REQUEST_DELAY = 2  # seconds between requests

# Output settings
OUTPUT_DIR = "output"
DATA_DIR = "data"
GRAPH_DIR = "graphs"
