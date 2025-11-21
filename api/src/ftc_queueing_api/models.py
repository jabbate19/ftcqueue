from sqlmodel import Field, SQLModel
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Column, TEXT, BIGINT

class DebugLogs(SQLModel, table=True):
    """
    Logs for debugging purposes from agents
    """

    id: int | None = Field(default=None, primary_key=True)
    time: datetime = Field(default_factory=lambda: datetime.now())
    event: str
    payload: str = Field(sa_column=Column(TEXT))
    headers: str | None = Field(default_factory=lambda: None, sa_column=Column(TEXT))

class MatchData(SQLModel, table=True):
    """
    Inner data about a match from FTC Scoring System Dump
    """

    matchNumber: int = Field(primary_key=True)
    matchName: str
    field: int
    red1: int
    red2: int
    blue1: int
    blue2: int
    has_pinged: bool = Field(default=False)

class AgentInitializePayload(BaseModel):
    teams: list[int]
    matches: list[MatchData]

class UpdateMatchPayload(BaseModel):
    """
    Inner data about a match from FTC Scoring System Websocket
    """

    number: int
    shortName: str
    field: int

class AgentUpdatePayload(BaseModel):
    """
    Full payload for a match update from FTC Scoring System Websocket
    """

    updateTime: int
    updateType: str
    payload: UpdateMatchPayload


class SendMessagePayload(BaseModel):
    """
    Used in admin request to send a message to Discord
    """

    content: str


class Team(SQLModel, table=True):
    """
    Maps team numbers to Discord Role IDs
    """

    team_number: int = Field(primary_key=True)
    discord_role_id: int = Field(sa_column=Column(BIGINT))
