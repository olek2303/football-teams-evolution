import requests
from bs4 import BeautifulSoup
import time
import random

headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

def get_total_pages(url):
    try:
        response = requests.get(url.format(1), headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')


        pagination_ul = soup.find('ul', class_='pagination')

        if not pagination_ul:
            return 1

        page_links = pagination_ul.find_all('a')

        page_numbers = []
        for link in page_links:
            text = link.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))

        if page_numbers:
            max_page = max(page_numbers)
            print(f"Found{max_page} pages")
            return max_page
        else:
            return 1

    except Exception as e:
        return 50


def find_match_links(team_name):

    # config
    base_url = "https://footballia.eu"
    list_url = "https://footballia.eu/teams/" + team_name + "?page={}"
    start_year = 1990
    end_year = 2022
    output_file = team_name + "_match_links.txt"



    collected_links = []


    # Find number of pages
    n_of_pages = get_total_pages(list_url)

    for page in range(1, n_of_pages + 1):

        try:
            response = requests.get(list_url.format(page), headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            rows = soup.find_all('tr')

            for row in rows:
                season_td = row.find('td', class_='season')

                if season_td:
                    season_text = season_td.get_text(strip=True)  # np. "1960-1961"

                    try:
                        season_start_year = int(season_text[:4])
                        if start_year <= season_start_year <= end_year:
                            match_td = row.find('td', class_='match')
                            if match_td:
                                link_div = match_td.find('div', class_='hidden-xs')
                                if link_div:
                                    link_tag = link_div.find('a', href=True)
                                    if link_tag:
                                        full_link = base_url + link_tag['href']
                                        collected_links.append(full_link)

                    except ValueError:
                        continue

            sleep_time = random.uniform(1, 3)
            time.sleep(sleep_time)

        except requests.exceptions.RequestException as e:
            print(f"Error while loading page number {page}: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        for link in collected_links:
            f.write(link + "\n")


def main():
    team_name = "fc-barcelona"
    find_match_links(team_name)

if __name__ == "__main__":
    main()