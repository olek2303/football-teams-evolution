from __future__ import annotations

import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import AppearanceDTO, MatchDTO, PlayerDTO, Provider, TeamDTO


class FootballiaProvider(Provider):
    name = "footballia"
    BASE = "https://footballia.eu"

    def __init__(
        self,
        timeout: float = 30.0,
        sleep_range: tuple[float, float] = (1.0, 2.5),
        max_workers: int = 5,
    ):
        self._log = structlog.get_logger(self.name)
        self._http = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                )
            },
        )
        self._sleep_range = sleep_range
        self._max_workers = max_workers

    def list_matches(self, team_names: list[str], date_from: str, date_to: str) -> list[MatchDTO]:
        self._log.info("list_matches.start", teams=team_names, date_from=date_from, date_to=date_to)
        date_from_parsed = self._parse_iso_date(date_from)
        date_to_parsed = self._parse_iso_date(date_to)

        team_slugs = [self._to_slug(t) for t in team_names]
        self._log.info("list_matches.team_slugs", team_slugs=team_slugs)
        links: set[str] = set()
        for slug in team_slugs:
            slug_links = self._list_match_links(slug, date_from_parsed, date_to_parsed)
            self._log.info("list_matches.team_links", team_slug=slug, count=len(slug_links))
            links.update(slug_links)

        out: list[MatchDTO] = []
        seen_matches: set[str] = set()
        sorted_links = sorted(links)

        # Fetch metadata in parallel using thread pool
        self._log.info(
            "list_matches.fetch_metadata.start",
            link_count=len(sorted_links),
            workers=self._max_workers,
        )
        processed = 0
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all metadata fetch tasks
            future_to_link = {
                executor.submit(self._scrape_match_metadata, link): link
                for link in sorted_links
                if self._match_id_from_url(link) not in seen_matches
            }

            # Process results as they complete
            for future in as_completed(future_to_link):
                processed += 1
                link = future_to_link[future]
                match_id = self._match_id_from_url(link)
                if match_id in seen_matches:
                    continue

                try:
                    meta = future.result()
                except Exception as e:
                    self._log.warn("list_matches.metadata_fetch_error", url=link, error=str(e))
                    continue

                if not meta:
                    self._log.warn("list_matches.metadata_missing", url=link)
                    continue

                match_date = meta["match_date"]
                if not match_date:
                    self._log.warn("list_matches.match_date_missing", url=link)
                    continue

                if not self._date_in_range(match_date, date_from_parsed, date_to_parsed):
                    self._log.info("list_matches.out_of_range", url=link, match_date=match_date)
                    continue

                home_team = TeamDTO(
                    source=self.name,
                    source_team_id=meta["home_team_id"],
                    name=meta["home_team_name"],
                )
                away_team = TeamDTO(
                    source=self.name,
                    source_team_id=meta["away_team_id"],
                    name=meta["away_team_name"],
                )

                match_dto = MatchDTO(
                    source=self.name,
                    source_match_id=match_id,
                    match_date=match_date,
                    season=meta.get("season"),
                    competition=meta.get("competition"),
                    home=home_team,
                    away=away_team,
                )
                out.append(match_dto)
                seen_matches.add(match_id)

                if processed % 50 == 0:
                    self._log.info(
                        "list_matches.fetch_metadata.progress",
                        processed=processed,
                        total=len(future_to_link),
                        matches_found=len(out),
                    )
                self._log.info(
                    "list_matches.match_parsed",
                    home=home_team.name,
                    away=away_team.name,
                    date=match_date,
                    season=meta.get("season"),
                )

        self._log.info("list_matches.done", match_count=len(out), total_processed=processed)
        return out

    def get_lineups(self, source_match_id: str) -> list[AppearanceDTO]:
        url = f"{self.BASE}/matches/{source_match_id}"
        self._log.info("get_lineups.start", match_id=source_match_id, url=url)
        soup = self._fetch_soup(url)
        if not soup:
            self._log.warn("get_lineups.fetch_failed", match_id=source_match_id, url=url)
            return []

        home_team_name, home_team_id = self._extract_team(soup, "homeTeam")
        away_team_name, away_team_id = self._extract_team(soup, "awayTeam")

        home_team = TeamDTO(
            source=self.name,
            source_team_id=home_team_id,
            name=home_team_name,
        )
        away_team = TeamDTO(
            source=self.name,
            source_team_id=away_team_id,
            name=away_team_name,
        )

        appearances: list[AppearanceDTO] = []
        players_div = soup.find("div", class_="players")
        if not players_div:
            self._log.warn("get_lineups.players_missing", match_id=source_match_id)
            return appearances

        team_columns = players_div.find_all("td", width="45%")
        for idx, col in enumerate(team_columns):
            player_links = col.find_all("a", href=True)
            is_home = idx % 2 == 0
            team = home_team if is_home else away_team

            players = []
            for link in player_links:
                href = link.get("href", "")
                if "/players/" not in href:
                    continue
                player_name = link.get_text(strip=True)
                player_id = self._player_id_from_href(href, player_name)
                players.append((player_name, player_id))

            for i, (player_name, player_id) in enumerate(players):
                player = PlayerDTO(
                    source=self.name,
                    source_player_id=player_id,
                    name=player_name,
                )
                appearances.append(
                    AppearanceDTO(
                        player=player,
                        team=team,
                        is_starter=i < 11,
                    )
                )

        return appearances

    def _list_match_links(
        self,
        team_slug: str,
        date_from: date | None,
        date_to: date | None,
    ) -> set[str]:
        list_url = f"{self.BASE}/teams/{team_slug}?page={{}}"
        n_pages = self._get_total_pages(list_url)
        self._log.info("list_match_links.pages", team_slug=team_slug, pages=n_pages)

        min_year = date_from.year if date_from else None
        max_year = date_to.year if date_to else None

        links: set[str] = set()
        for page in range(1, n_pages + 1):
            soup = self._fetch_soup(list_url.format(page))
            if not soup:
                self._log.warn("list_match_links.page_failed", team_slug=team_slug, page=page)
                continue

            page_links = 0
            rows = soup.find_all("tr")
            for row in rows:
                season_td = row.find("td", class_="season")
                if season_td:
                    season_text = season_td.get_text(strip=True)
                    season_start = self._season_start_year(season_text)
                    if season_start is not None:
                        if min_year is not None and season_start < min_year:
                            continue
                        if max_year is not None and season_start > max_year:
                            continue

                match_td = row.find("td", class_="match")
                if not match_td:
                    continue

                link_div = match_td.find("div", class_="hidden-xs")
                if not link_div:
                    continue

                link_tag = link_div.find("a", href=True)
                if not link_tag:
                    continue

                href = link_tag["href"]
                links.add(self.BASE + href)
                page_links += 1

            self._log.info(
                "list_match_links.page_done",
                team_slug=team_slug,
                page=page,
                page_num=page,
                total_pages=n_pages,
                links_on_page=page_links,
                cumulative_links=len(links),
            )
            self._polite_sleep()

        self._log.info("list_match_links.done", team_slug=team_slug, total_links=len(links))
        return links

    def _get_total_pages(self, list_url: str) -> int:
        soup = self._fetch_soup(list_url.format(1))
        if not soup:
            self._log.warn("get_total_pages.fetch_failed", url=list_url)
            return 1

        pagination_ul = soup.find("ul", class_="pagination")
        if not pagination_ul:
            return 1

        page_numbers: list[int] = []
        for link in pagination_ul.find_all("a"):
            text = link.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))

        return max(page_numbers) if page_numbers else 1

    def _scrape_match_metadata(self, url: str) -> dict[str, str | None] | None:
        soup = self._fetch_soup(url)
        if not soup:
            self._log.warn("scrape_match_metadata.fetch_failed", url=url)
            return None

        match_date = self._extract_match_date(soup)
        home_name, home_id = self._extract_team(soup, "homeTeam")
        away_name, away_id = self._extract_team(soup, "awayTeam")

        competition = self._extract_competition(soup)
        season = self._extract_season_from_url(url) or self._extract_season_from_text(soup)

        return {
            "match_date": match_date,
            "home_team_name": home_name,
            "home_team_id": home_id,
            "away_team_name": away_name,
            "away_team_id": away_id,
            "competition": competition,
            "season": season,
        }

    def _extract_team(self, soup: BeautifulSoup, itemprop: str) -> tuple[str, str]:
        team_div = soup.find("div", itemprop=itemprop)
        if not team_div:
            return "Unknown", "unknown"

        team_name = team_div.get_text(strip=True)
        link = team_div.find("a", href=True)
        if link and "/teams/" in link["href"]:
            team_id = self._team_id_from_href(link["href"], team_name)
        else:
            team_id = self._to_slug(team_name)
        return team_name, team_id

    def _extract_match_date(self, soup: BeautifulSoup) -> str | None:
        candidates: list[str] = []

        # Check for div with class "playing_date" and content attribute (Footballia format)
        playing_date_div = soup.find("div", class_="playing_date")
        if playing_date_div and playing_date_div.get("content"):
            candidates.append(playing_date_div.get("content", ""))
        if playing_date_div and playing_date_div.get_text(strip=True):
            candidates.append(playing_date_div.get_text(strip=True))

        meta_date = soup.find("meta", itemprop="startDate")
        if meta_date and meta_date.get("content"):
            candidates.append(meta_date.get("content", ""))

        time_date = soup.find("time", itemprop="startDate")
        if time_date and time_date.get("datetime"):
            candidates.append(time_date.get("datetime", ""))
        if time_date and time_date.get_text(strip=True):
            candidates.append(time_date.get_text(strip=True))

        for cls in ("date", "game-date", "match-date"):
            node = soup.find("div", class_=cls) or soup.find("span", class_=cls)
            if node and node.get_text(strip=True):
                candidates.append(node.get_text(strip=True))

        for raw in candidates:
            parsed = self._parse_flexible_date(raw)
            if parsed:
                return parsed

        return None

    def _extract_competition(self, soup: BeautifulSoup) -> str | None:
        for cls in ("competition", "tournament", "match-competition"):
            node = soup.find("div", class_=cls) or soup.find("span", class_=cls)
            if node and node.get_text(strip=True):
                competition_text = node.get_text(strip=True)
                # Remove season suffix (e.g., "1991-1992" or "2004-2005")
                competition_text = re.sub(r"\s*\d{4}-\d{4}\s*$", "", competition_text)
                # Remove single year suffix (e.g., "Audi Cup2011" or "Audi Cup 2011")
                competition_text = re.sub(r"\s*\d{4}\s*$", "", competition_text)
                return competition_text.strip()
        return None

    def _extract_season_from_url(self, url: str) -> str | None:
        match = re.search(r"-(\d{4}-\d{4})$", url)
        if match:
            return match.group(1)
        return None

    def _extract_season_from_text(self, soup: BeautifulSoup) -> str | None:
        season_node = soup.find("span", class_="season")
        if season_node and season_node.get_text(strip=True):
            text = season_node.get_text(strip=True)
            match = re.search(r"\d{4}-\d{4}", text)
            if match:
                return match.group(0)
        return None

    def _parse_iso_date(self, value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except Exception:
            return None

    def _parse_flexible_date(self, value: str) -> str | None:
        value = value.strip()
        if not value:
            return None

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except Exception:
                continue

        match = re.search(r"(\d{4}-\d{2}-\d{2})", value)
        if match:
            return match.group(1)
        return None

    def _season_start_year(self, season_text: str) -> int | None:
        if not season_text:
            return None
        match = re.search(r"^(\d{4})", season_text)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
        return None

    def _date_in_range(self, match_date: str, date_from: date | None, date_to: date | None) -> bool:
        parsed = self._parse_iso_date(match_date)
        if not parsed:
            return False
        if date_from and parsed < date_from:
            return False
        if date_to and parsed > date_to:
            return False
        return True

    def _fetch_soup(self, url: str) -> BeautifulSoup | None:
        try:
            response = self._http.get(url)
            response.raise_for_status()
        except Exception:
            self._log.warn("fetch_failed", url=url)
            return None
        return BeautifulSoup(response.text, "html.parser")

    def _match_id_from_url(self, url: str) -> str:
        return url.rstrip("/").split("/matches/")[-1]

    def _team_id_from_href(self, href: str, name: str) -> str:
        slug = href.rstrip("/").split("/teams/")[-1]
        return slug or self._to_slug(name)

    def _player_id_from_href(self, href: str, name: str) -> str:
        slug = href.rstrip("/").split("/players/")[-1]
        return slug or self._to_slug(name)

    def _to_slug(self, name: str) -> str:
        slug = name.strip().lower()
        slug = re.sub(r"[\'\"\.]", "", slug)
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")

    def _polite_sleep(self) -> None:
        low, high = self._sleep_range
        time.sleep(random.uniform(low, high))
