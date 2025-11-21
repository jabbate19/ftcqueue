from sqlmodel import Field, SQLModel
from pydantic import BaseModel
from datetime import datetime


class DebugLogs(SQLModel):
    """
    Logs for debugging purposes from agents
    """

    id: int | None = Field(default=None, primary_key=True)
    time: datetime = Field(default_factory=lambda: datetime.now())
    event: str
    payload: str
    headers: str | None = None


class MatchPayload(BaseModel):
    """
    Inner data about a match from FTC Scoring System Weboscket
    """

    number: int
    shortName: str
    field: int


class UpdatePayload(BaseModel):
    """
    Full payload for a match update from FTC Scoring System Weboscket
    """

    updateTime: int
    updateType: str
    status: str
    payload: MatchPayload


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
    discord_role_id: int
