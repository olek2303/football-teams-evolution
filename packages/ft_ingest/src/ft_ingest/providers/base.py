from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TeamDTO:
    source: str
    source_team_id: str
    name: str
    country: str | None = None


@dataclass(frozen=True)
class PlayerDTO:
    source: str
    source_player_id: str
    name: str
    birth_date: str | None = None
    nationality: str | None = None


@dataclass(frozen=True)
class MatchDTO:
    source: str
    source_match_id: str
    match_date: str
    season: str | None
    competition: str | None
    home: TeamDTO
    away: TeamDTO


@dataclass(frozen=True)
class AppearanceDTO:
    player: PlayerDTO
    team: TeamDTO
    is_starter: bool
    minutes: int | None = None
    position: str | None = None


class Provider(Protocol):
    name: str

    def list_matches(
        self, team_names: list[str], date_from: str, date_to: str
    ) -> Iterable[MatchDTO]: ...

    def get_lineups(self, source_match_id: str) -> list[AppearanceDTO]: ...
