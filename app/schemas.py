from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class StadiumBase(BaseModel):
    name: str
    city: Optional[str] = None
    capacity: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class StadiumResponse(StadiumBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class TeamBase(BaseModel):
    name: str
    short_name: Optional[str] = None
    city: Optional[str] = None
    colors: Optional[str] = None
    founded: Optional[int] = None
    logo_url: Optional[str] = None

class TeamResponse(TeamBase):
    id: int
    stadium: Optional[StadiumResponse] = None
    model_config = ConfigDict(from_attributes=True)

class PlayerBase(BaseModel):
    name: str
    position: Optional[str] = None
    number: Optional[int] = None
    nationality: Optional[str] = None
    birth_date: Optional[str] = None
    photo_url: Optional[str] = None

class PlayerResponse(PlayerBase):
    id: int
    team_id: int
    model_config = ConfigDict(from_attributes=True)

class MatchBase(BaseModel):
    home_team_id: int
    away_team_id: int
    match_date: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = "scheduled"
    week_number: Optional[int] = None
    sofascore_event_id: Optional[int] = None

class MatchResponse(MatchBase):
    id: int
    home_team: Optional[TeamResponse] = None
    away_team: Optional[TeamResponse] = None
    model_config = ConfigDict(from_attributes=True)

class StandingResponse(BaseModel):
    position: int
    team: TeamResponse
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    model_config = ConfigDict(from_attributes=True)

class TopScorerResponse(BaseModel):
    id: int
    player: str
    team: Optional[str] = None
    goals: int
    assists: Optional[int] = None
    matches: Optional[int] = None
    penalties: Optional[int] = None
    season: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class NewsResponse(BaseModel):
    id: int
    title: str
    link: str
    description: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class MatchStatResponse(BaseModel):
    id: int
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    event_id: Optional[str] = None
    season: Optional[str] = None
    possession: Optional[float] = None
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    corners: Optional[int] = None
    fouls: Optional[int] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    offsides: Optional[int] = None
    saves: Optional[int] = None
    passes: Optional[int] = None
    total_passes: Optional[int] = None
    tackles: Optional[int] = None
    interceptions: Optional[int] = None
    blocked_shots: Optional[int] = None
    crosses: Optional[int] = None
    long_balls: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class PlayerStatResponse(BaseModel):
    id: int
    player_id: Optional[int] = None
    player_name: str
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    season: Optional[str] = None
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    matches_played: int
    model_config = ConfigDict(from_attributes=True)


class MatchEventResponse(BaseModel):
    id: int
    event_type: str
    event_time: Optional[int] = None
    player_name: Optional[str] = None
    player_id: Optional[int] = None
    team_name: Optional[str] = None
    team_id: Optional[int] = None
    description: Optional[str] = None
    is_home: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class MatchLineupResponse(BaseModel):
    id: int
    player_name: Optional[str] = None
    player_id: Optional[int] = None
    team_name: Optional[str] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    is_substitute: int = 0
    jersey_number: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
