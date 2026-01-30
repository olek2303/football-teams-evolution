from __future__ import annotations

import httpx

from .base import AppearanceDTO, MatchDTO, PlayerDTO, Provider, TeamDTO


class StatsBombOpenData(Provider):
    name = "statsbomb_open_data"
    BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

    def __init__(self, timeout: float = 30.0):
        self._http = httpx.Client(timeout=timeout)

    def list_matches(self, team_names: list[str], date_from: str, date_to: str) -> list[MatchDTO]:
        """Fetch matches for given teams within date range from StatsBomb open data."""
        # StatsBomb organizes matches by season/competition in JSON files
        # We need to fetch the matches index and filter by team and date
        url = f"{self.BASE}/matches/index.json"

        try:
            index = self._http.get(url).json()
        except Exception as e:
            raise ValueError(f"Failed to fetch matches index from {url}: {e}")

        out: list[MatchDTO] = []
        team_names_set = set(t.lower() for t in team_names)

        # Process each season/competition combination
        for season_comp in index:
            season = season_comp.get("season_id")
            competition = season_comp.get("competition_id")
            matches_file = season_comp.get("matches")

            if not matches_file:
                continue

            # Fetch matches for this season/competition
            match_url = f"{self.BASE}/matches/{matches_file}"
            try:
                matches = self._http.get(match_url).json()
            except Exception:
                continue

            # Filter matches by team and date
            for match_data in matches:
                match_date = match_data.get("match_date", "")

                # Check if match is within date range
                if not (date_from <= match_date <= date_to):
                    continue

                home_name = match_data.get("home_team", {}).get("home_team_name", "").lower()
                away_name = match_data.get("away_team", {}).get("away_team_name", "").lower()

                # Check if either team matches the filter
                if home_name in team_names_set or away_name in team_names_set:
                    home_team = TeamDTO(
                        source=self.name,
                        source_team_id=str(match_data["home_team"]["home_team_id"]),
                        name=match_data["home_team"]["home_team_name"],
                    )
                    away_team = TeamDTO(
                        source=self.name,
                        source_team_id=str(match_data["away_team"]["away_team_id"]),
                        name=match_data["away_team"]["away_team_name"],
                    )

                    out.append(
                        MatchDTO(
                            source=self.name,
                            source_match_id=str(match_data["match_id"]),
                            match_date=match_date,
                            season=str(season) if season else None,
                            competition=str(competition) if competition else None,
                            home=home_team,
                            away=away_team,
                        )
                    )

        return out

    def get_lineups(self, source_match_id: str) -> list[AppearanceDTO]:
        url = f"{self.BASE}/lineups/{source_match_id}.json"
        data = self._http.get(url).json()

        out: list[AppearanceDTO] = []
        for team_block in data:
            team = TeamDTO(
                source=self.name,
                source_team_id=str(team_block["team_id"]),
                name=team_block["team_name"],
            )
            for p in team_block["lineup"]:
                player = PlayerDTO(
                    source=self.name,
                    source_player_id=str(p["player_id"]),
                    name=p["player_name"],
                )
                out.append(
                    AppearanceDTO(
                        player=player,
                        team=team,
                        is_starter=bool(p.get("positions")),
                        position=(p["positions"][0]["position"] if p.get("positions") else None),
                    )
                )
        return out
