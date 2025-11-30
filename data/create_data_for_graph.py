import pandas as pd
import ast
from itertools import combinations
from collections import Counter


def main():
    team_name = "fc-barcelona"
    # team_keyword -> to find if home or away team
    team_keyword = "FC Barcelona"
    input_file = "./files/" + team_name + "_match_data.csv"
    output_file = "./files/" + team_name + "_edges.csv"
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print("CSV file not found")
        return

    pair_counter = Counter()
    matches_count = 0


    for index, row in df.iterrows():
        my_team_players = []

        home_team = str(row.get('home_team', ''))
        away_team = str(row.get('away_team', ''))

        if team_keyword in home_team:
            raw_players = row.get('home_players', "[]")
        elif team_keyword in away_team:
            raw_players = row.get('away_players', "[]")
        else:
            continue

        try:
            if isinstance(raw_players, str):
                players_list = ast.literal_eval(raw_players)
            else:
                players_list = raw_players
        except (ValueError, SyntaxError):
            continue

        if len(players_list) > 1:
            sorted_players = sorted(players_list)

            pairs = combinations(sorted_players, 2)

            pair_counter.update(pairs)
            matches_count += 1

    print(f" Analyzed {matches_count} matches.")


    edges_data = []
    for (p1, p2), weight in pair_counter.items():
        edges_data.append({
            'Source': p1,
            'Target': p2,
            'Weight': weight,
            'Type': 'Undirected'
        })

    edges_df = pd.DataFrame(edges_data)

    edges_df = edges_df.sort_values(by='Weight', ascending=False)

    edges_df.to_csv(output_file, index=False)

    print(edges_df.head(5))


if __name__ == "__main__":
    main()