import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_footballia_match(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"downloading data from: {url}")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"connection error: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    match_data = {
        'match_url': url,
        'home_team': 'Unknown',
        'away_team': 'Unknown',
        'home_players': [],
        'away_players': [],
        'result': 'Unknown',
        'goal_scorers_home': [],
        'goal_scorers_away': [],
    }

    player_links = soup.find_all('a', href=True)

    home_section = soup.find('div', itemprop='homeTeam')
    if home_section:
        match_data['home_team'] = home_section.text.strip()

    away_section = soup.find('div', itemprop='awayTeam')
    if away_section:
        match_data['away_team'] = away_section.text.strip()

    players_div = soup.find('div', class_='players')
    if players_div:
        team_columns = players_div.find_all('td', width='45%')

        for i, col in enumerate(team_columns):
            player_links = col.find_all('a', href=True)

            for link in player_links:
                if '/players/' in link['href']:
                    player_name = link.get_text(strip=True)

                    if i % 2 == 0:
                        match_data['home_players'].append(player_name)
                    else:
                        match_data['away_players'].append(player_name)

    result_div = soup.find('div', class_='result')
    if result_div:
        score_span = result_div.find('span')
        if score_span and score_span.contents:
            match_data['result'] = str(score_span.contents[0]).strip().replace('"', '')

        goals_container = result_div.find('div', class_='goals')
        if goals_container:
            goals = goals_container.find_all('div', class_=lambda x: x and 'goal' in x)

            for goal in goals:
                name_span = goal.find('span', title=True)
                if name_span:
                    scorer_name = name_span['title']
                    classes = goal.get('class', [])

                    if 'home' in classes:
                        match_data['goal_scorers_home'].append(scorer_name)
                    elif 'away' in classes:
                        match_data['goal_scorers_away'].append(scorer_name)

    return match_data


sample_url = "https://footballia.eu/matches/rcd-mallorca-fc-barcelona-liga-1-division-2023-2024"

data = scrape_footballia_match(sample_url)

if data and data['home_players']:
    print("\n--- results ---")
    print(f"match: {data['home_team']} vs {data['away_team']}")

    formatted_data = {
        'match_url': [data['match_url']],
        'home_team': [data['home_team']],
        'away_team': [data['away_team']],
        'home_players': [data['home_players']],
        'away_players': [data['away_players']],
        'result': [data['result']],
        'goal_scorers_home': [data['goal_scorers_home']],
        'goal_scorers_away': [data['goal_scorers_away']]
    }

    df = pd.DataFrame(formatted_data)
    df.to_csv("./files/example_match_data.csv", index=False)

else:
    print("error scraping match data")
