from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Protocol

@dataclass(frozen=True)
class TeamDTO:
    source: str
    source_team_id: str
    name: str
    country: Optional[str] = None

@dataclass(frozen=True)
class PlayerDTO:
    source: str
    source_player_id: str
    name: str
    birth_date: Optional[str] = None
    nationality: Optional[str] = None

@dataclass(frozen=True)
class MatchDTO:
    source: str
    source_match_id: str
    match_date: str
    season: Optional[str]
    competition: Optional[str]
    home: TeamDTO
    away: TeamDTO

@dataclass(frozen=True)
class AppearanceDTO:
    player: PlayerDTO
    team: TeamDTO
    is_starter: bool
    minutes: Optional[int] = None
    position: Optional[str] = None

class Provider(Protocol):
    name: str

    def list_matches(
        self,
        team_names: list[str],
        date_from: str,
        date_to: str
    ) -> Iterable[MatchDTO]:
        ...

    def get_lineups(self, source_match_id: str) -> list[AppearanceDTO]:
        ...
