from __future__ import annotations

import httpx
import structlog

from .base import AppearanceDTO, MatchDTO, PlayerDTO, Provider, TeamDTO


class StatsBombOpenData(Provider):
    name = "statsbomb_open_data"
    BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

    def __init__(self, timeout: float = 30.0):
        self._http = httpx.Client(timeout=timeout)
        self.log = structlog.get_logger(self.name)

    @staticmethod
    def _parse_time_to_minutes(time_str: str | None) -> float | None:
        """Parse time string in format 'MM:SS' to minutes as float."""
        if not time_str:
            return None
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes + (seconds / 60.0)
            return None
        except (ValueError, AttributeError):
            return None

    def _calculate_minutes_played(self, positions: list[dict] | None) -> int | None:
        """Calculate total minutes played across all positions.
        
        Args:
            positions: List of position dictionaries with 'from' and 'to' times
            
        Returns:
            Total minutes played, rounded to nearest integer, or None if no positions
        """
        if not positions:
            return None
        
        total_minutes = 0.0
        for pos in positions:
            from_time = self._parse_time_to_minutes(pos.get("from"))
            to_time = self._parse_time_to_minutes(pos.get("to"))
            
            # If 'to' is None, assume played until end (typically 90+ minutes)
            # We'll use a reasonable default based on typical match length
            if from_time is not None:
                if to_time is None:
                    # Assume match ended at 90 minutes if no end time specified
                    to_time = 90.0
                
                # Calculate duration for this position
                duration = to_time - from_time
                if duration > 0:
                    total_minutes += duration
        
        self.log.debug("calculated_minutes", total=total_minutes, positions_count=len(positions))
        return round(total_minutes) if total_minutes > 0 else None

    def list_matches(self, team_names: list[str], date_from: str, date_to: str) -> list[MatchDTO]:
        """Fetch matches for given teams within date range from StatsBomb open data.
        
        Data structure:
        - competitions.json: Contains competition and season info
        - matches/{competition_id}/{season_id}.json: Match files organized by competition and season
        """
        self.log.info("starting_match_list", teams=team_names, date_from=date_from, date_to=date_to)
        
        # Fetch competitions and seasons
        competitions_url = f"{self.BASE}/competitions.json"
        try:
            self.log.debug("fetching_competitions", url=competitions_url)
            competitions = self._http.get(competitions_url).json()
            self.log.debug("fetched_competitions", count=len(competitions))
        except Exception as e:
            self.log.error("failed_fetch_competitions", url=competitions_url, error=str(e))
            raise ValueError(f"Failed to fetch competitions from {competitions_url}: {e}")

        out: list[MatchDTO] = []
        team_names_set = set(t.lower() for t in team_names)
        fetch_all = len(team_names_set) == 0  # If no teams specified, fetch all
        
        total_competitions = len(competitions)
        self.log.info("processing_competitions", total=total_competitions, fetch_all=fetch_all)

        # Process each competition and season
        for idx, competition in enumerate(competitions, 1):
            competition_id = competition.get("competition_id")
            competition_name = competition.get("competition_name", "")
            
            season_id = competition.get("season_id")
            season_name = competition.get("season_name", "")
            
            self.log.info(
                "processing_competition",
                progress=f"{idx}/{total_competitions}",
                competition=competition_name,
                season=season_name,
                matches_collected=len(out)
            )

            # Construct path: matches/{competition_id}/{season_id}.json
            match_url = f"{self.BASE}/matches/{competition_id}/{season_id}.json"
            
            try:
                self.log.debug("fetching_matches", competition=competition_name, season=season_name, url=match_url)
                matches = self._http.get(match_url).json()
                self.log.info(
                    "fetched_matches",
                    competition=competition_name,
                    season=season_name,
                    count=len(matches),
                    progress=f"{idx}/{total_competitions}"
                )
            except Exception as e:
                self.log.warning("failed_fetch_matches", competition=competition_name, season=season_name, error=str(e))
                continue
            
            # Filter matches by team and date
            matches_before_filter = len(out)
            for match_data in matches:
                match_date = match_data.get("match_date", "")

                # Check if match is within date range
                if not (date_from <= match_date <= date_to):
                    continue

                home_team_data = match_data.get("home_team", {})
                away_team_data = match_data.get("away_team", {})
                
                home_name = home_team_data.get("home_team_name", "").lower()
                away_name = away_team_data.get("away_team_name", "").lower()

                # Check if either team matches the filter (or fetch all if no filter)
                if fetch_all or home_name in team_names_set or away_name in team_names_set:
                    if not fetch_all:
                        self.log.debug(
                            "matched_team",
                            competition=competition_name,
                            season=season_name,
                            home=home_name,
                            away=away_name,
                            match_date=match_date
                        )
                    home_team = TeamDTO(
                        source=self.name,
                        source_team_id=str(home_team_data["home_team_id"]),
                        name=home_team_data["home_team_name"],
                    )
                    away_team = TeamDTO(
                        source=self.name,
                        source_team_id=str(away_team_data["away_team_id"]),
                        name=away_team_data["away_team_name"],
                    )

                    out.append(
                        MatchDTO(
                            source=self.name,
                            source_match_id=str(match_data["match_id"]),
                            match_date=match_date,
                            season=season_name,
                            competition=competition_name,
                            home=home_team,
                            away=away_team,
                        )
                    )

            # Log matches added from this competition/season
            matches_added = len(out) - matches_before_filter
            if matches_added > 0:
                self.log.info(
                    "competition_filtered",
                    competition=competition_name,
                    season=season_name,
                    matches_added=matches_added,
                    total_collected=len(out)
                )

        self.log.info("completed_match_list", total_matches=len(out), competitions_processed=total_competitions)
        return out

    def get_lineups(self, source_match_id: str) -> list[AppearanceDTO]:
        self.log.info("fetching_lineups", match_id=source_match_id)
        url = f"{self.BASE}/lineups/{source_match_id}.json"
        
        try:
            self.log.debug("fetching_lineups_data", url=url)
            data = self._http.get(url).json()
        except Exception as e:
            self.log.error("failed_fetch_lineups", match_id=source_match_id, error=str(e))
            raise

        out: list[AppearanceDTO] = []
        for team_block in data:
            team = TeamDTO(
                source=self.name,
                source_team_id=str(team_block["team_id"]),
                name=team_block["team_name"],
            )
            team_appearances = 0
            for p in team_block["lineup"]:
                player = PlayerDTO(
                    source=self.name,
                    source_player_id=str(p["player_id"]),
                    name=p["player_name"],
                    nationality=p["country"]["name"] if p.get("country") else None,
                )
                
                # Calculate minutes played from positions data
                positions = p.get("positions", [])
                minutes_played = self._calculate_minutes_played(positions)
                
                out.append(
                    AppearanceDTO(
                        player=player,
                        team=team,
                        is_starter=bool(positions),
                        position=(positions[0]["position"] if positions else None),
                        minutes=minutes_played,
                    )
                )
                team_appearances += 1
            self.log.debug("processed_team_lineup", team=team.name, appearances=team_appearances)
        
        self.log.info("completed_lineups", match_id=source_match_id, total_appearances=len(out))
        return out
