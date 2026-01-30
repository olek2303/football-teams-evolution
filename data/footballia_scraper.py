import random
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup


def scrape_footballia_match(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"downloading data from: {url}")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"connection error: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    match_data = {
        "match_url": url,
        "home_team": "Unknown",
        "away_team": "Unknown",
        "home_players": [],
        "away_players": [],
        "result": "Unknown",
        "goal_scorers_home": [],
        "goal_scorers_away": [],
    }

    player_links = soup.find_all("a", href=True)

    home_section = soup.find("div", itemprop="homeTeam")
    if home_section:
        match_data["home_team"] = home_section.text.strip()

    away_section = soup.find("div", itemprop="awayTeam")
    if away_section:
        match_data["away_team"] = away_section.text.strip()

    players_div = soup.find("div", class_="players")
    if players_div:
        team_columns = players_div.find_all("td", width="45%")

        for i, col in enumerate(team_columns):
            player_links = col.find_all("a", href=True)

            for link in player_links:
                if "/players/" in link["href"]:
                    player_name = link.get_text(strip=True)

                    if i % 2 == 0:
                        match_data["home_players"].append(player_name)
                    else:
                        match_data["away_players"].append(player_name)

    result_div = soup.find("div", class_="result")
    if result_div:
        score_span = result_div.find("span")
        if score_span and score_span.contents:
            match_data["result"] = str(score_span.contents[0]).strip().replace('"', "")

        goals_container = result_div.find("div", class_="goals")
        if goals_container:
            goals = goals_container.find_all("div", class_=lambda x: x and "goal" in x)

            for goal in goals:
                name_span = goal.find("span", title=True)
                if name_span:
                    scorer_name = name_span["title"]
                    classes = goal.get("class", [])

                    if "home" in classes:
                        match_data["goal_scorers_home"].append(scorer_name)
                    elif "away" in classes:
                        match_data["goal_scorers_away"].append(scorer_name)

    return match_data


def main():
    team_name = "fc-barcelona"

    match_links_file_name = team_name + "_match_links.txt"
    output_csv = "files/" + team_name + "match_data.csv"
    with open(match_links_file_name) as f:
        urls_to_scrape = f.read().splitlines()

    all_matches_data = []

    for url in urls_to_scrape:
        data = scrape_footballia_match(url)  # Twoja funkcja
        if data:
            all_matches_data.append(data)

        time.sleep(random.uniform(1.5, 3.5))

    if all_matches_data:
        df = pd.DataFrame(all_matches_data)
        df.to_csv(output_csv, index=False)

    else:
        print("No data found!")


if __name__ == "__main__":
    main()
