from fastapi import FastAPI, Depends, HTTPException, Security, Request, Response, Body
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from sqlmodel import Session, SQLModel, create_engine, select, delete
from .models import AgentUpdatePayload, DebugLogs, Team, SendMessagePayload, AgentInitializePayload, MatchData
import json
from typing import Any
from time import sleep
from contextlib import asynccontextmanager
from .discord import (
    verify_signature,
    parse_command,
    register_global_commands,
    get_global_commands,
    create_team_role,
    send_message,
    delete_team_role,
)
from datetime import datetime
from . import config
import logging

AGENT_API_KEY = config.AGENT_API_KEY
AGENT_API_KEY_NAME = "X-AGENT-KEY"
ADMIN_API_KEY = config.ADMIN_API_KEY
ADMIN_API_KEY_NAME = "X-ADMIN-KEY"

# Security dependency
agent_api_key_header = APIKeyHeader(
    name=AGENT_API_KEY_NAME, scheme_name="agent-key", auto_error=False
)
admin_api_key_header = APIKeyHeader(
    name=ADMIN_API_KEY_NAME, scheme_name="admin-key", auto_error=False
)

sql_uri = config.SQL_URI

engine = create_engine(sql_uri, echo=True)

QUEUE_LOOK_FORWARD = 3
QUEUE_MESSAGE_TEMPLATES = [
    "{teams}, match {match} is next on field {field}!",
    "{teams}, match {match} is queueing on field {field}!",
    "{teams}, match {match} is queueing on field {field}!",
]


async def get_agent_api_key(api_key_header: str = Security(agent_api_key_header)):
    if api_key_header == AGENT_API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate Agent API Key"
        )


async def get_admin_api_key(api_key_header: str = Security(admin_api_key_header)):
    if api_key_header == ADMIN_API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate Agent API Key"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    register_global_commands()
    yield


app = FastAPI(lifespan=lifespan)

@app.post("/api/v1/initialize")
async def initialize(payload: AgentInitializePayload, api_key: str = Depends(get_agent_api_key)):
    """
    Intakes initial payload from FTC Scoring system agent.
    """
    with Session(engine) as session:
        session.add(DebugLogs(event="scoring", payload=json.dumps(payload.model_dump(mode='json'))))
        session.commit()
        for team_number in payload.teams:
            team = session.get(Team, team_number)
            if not team:
                role_id = create_team_role(team_number)
                session.add(Team(team_number=team_number, discord_role_id=role_id))
        for match in payload.matches:
            result = session.get(MatchData, (match.matchNumber))
            if result is None:
                result = match
            for key, value in match.dict(exclude_unset=True).items():
                setattr(result, key, value) 
            session.add(result)
        session.commit()

@app.post("/api/v1/update")
async def update(payload: dict[str, Any] = Body(...), api_key: str = Depends(get_agent_api_key)):
    """
    Intakes events from FTC Scoring system websocket. Forwarded by agent.
    """
    with Session(engine) as session:
        session.add(DebugLogs(event="scoring", payload=json.dumps(payload)))
        session.commit()
    parsed_payload = AgentUpdatePayload(**payload)
    if parsed_payload.updateType == "MATCH_START":
        with Session(engine) as session:
            matches = session.exec(select(MatchData).where(MatchData.matchNumber >= parsed_payload.payload.number).order_by(MatchData.matchNumber).limit(1+QUEUE_LOOK_FORWARD)).all()
            started_match = matches[0]
            if len(matches) == 1 or started_match.has_pinged:
                logging.info("No upcoming matches to queue. Skip ping.")
                started_match.has_pinged = True
                session.add(started_match)
                session.commit()
                return
            next_matches = matches[1:]
            all_teams = []
            for match in next_matches:
                all_teams.extend([match.red1, match.red2, match.blue1, match.blue2])
            team_data = session.exec(select(Team).where(Team.team_number.in_(all_teams))).all()
            team_discord_map = {team.team_number: team.discord_role_id for team in team_data}
            messages = []
            for template, match in zip(QUEUE_MESSAGE_TEMPLATES, next_matches):
                messages.append(
                    template.format(
                        teams=", ".join(
                            f"<@&{team_discord_map[tn]}>" for tn in [
                                match.red1, match.red2, match.blue1, match.blue2
                            ]
                        ),
                        match=match.matchName,
                        field=match.field,
                    )
                )
            send_message("\n".join(messages))
            started_match.has_pinged = True
            session.add(started_match)
            session.commit()
    return

@app.post("/api/v1/ping")
async def ping(api_key: str = Depends(get_agent_api_key)):
    """
    Intakes ping events from FTC Scoring system websocket. Forwarded by agent.
    """
    with Session(engine) as session:
        session.add(DebugLogs(event="scoring", payload="ping"))
        session.commit()
    return "OK"

@app.post("/api/v1/discord")
async def discord(request: Request, response: Response):
    """
    Handles Discord Interactions for Role Slash Commands.
    """
    body = str(await request.body(), "utf-8")
    headers = request.headers
    # Log for debugging
    with Session(engine) as session:
        session.add(
            DebugLogs(event="discord", payload=body, headers=json.dumps(dict(headers)))
        )
        session.commit()
    # Verify is from Discord
    if not verify_signature(body, headers):
        logging.error("Signature verification failed")
        response.status_code = 401
        return "Bad request signature"
    payload = json.loads(body)
    # Discord Ping
    if payload["type"] == 1:
        return {"type": 1}
    # Command Sent
    if payload["type"] == 2:
        with Session(engine) as session:
            return parse_command(session, payload)
    # Other methods we're not handling
    return {
        "type": 4,
        "data": {
            "tts": False,
            "content": "Error: Unknown Interaction Type",
            "embeds": [],
            "allowed_mentions": {"parse": []},
        },
    }


# === Admin Routes ===
@app.post("/api/v1/admin/register_teams")
async def register(payload: list[int], api_key: str = Depends(get_admin_api_key)):
    """
    Registers teams to ensure they have Discord Roles

    Returns dict with "skipped" and "created" lists of team numbers.
    Skipped indicates the role already existed.
    """
    skipped = []
    created = []
    with Session(engine) as session:
        for team_number in payload:
            team = session.get(Team, team_number)
            if team:
                skipped.append(team_number)
            if not team:
                role_id = create_team_role(team_number)
                session.add(Team(team_number=team_number, discord_role_id=role_id))
                created.append(team_number)
        session.commit()
    return {"skipped": skipped, "created": created}

@app.post("/api/v1/admin/reset")
async def reset(api_key: str = Depends(get_admin_api_key)):
    """
    Deletes all teams and matches from Discord and the database.
    
    Could take multiple attempts if Discord rate limits.
    """
    with Session(engine) as session:
        for team in session.exec(select(Team)).all():
            delete_team_role(team.discord_role_id)
            sleep(0.5)  # To avoid hitting rate limits
            session.delete(team)
        session.exec(delete(MatchData))
        session.commit()
    return "OK"


@app.post("/api/v1/admin/register_commands")
async def debug_register_global(api_key: str = Depends(get_admin_api_key)):
    """
    Admin debug command to (re)register global Discord slash commands.
    """
    return register_global_commands()


@app.post("/api/v1/admin/get_commands")
async def debug_get_global(api_key: str = Depends(get_admin_api_key)):
    """
    Admin debug command to get global Discord slash commands.
    """
    resp = get_global_commands()
    return {"body": resp.text, "status_code": resp.status_code}


@app.post("/api/v1/admin/send_message")
async def debug_send_message(
    payload: SendMessagePayload, api_key: str = Depends(get_admin_api_key)
):
    """
    Admin debug command to send arbitrary message to Discord channel.
    """
    resp = send_message(payload.content)
    return {"body": resp.text, "status_code": resp.status_code}


@app.post("/api/v1/diagnostics/agent_ping")
async def debug_agent_ping(
    api_key: str = Depends(get_admin_api_key)
):
    """
    Gets time since last message from scoring system agent
    """
    with Session(engine) as session:
        statement = (
            select(DebugLogs)
            .where(DebugLogs.event == "scoring")
            .order_by(DebugLogs.time.desc()) # type: ignore[attr-defined]
            .limit(1)
        )
        result = session.exec(statement).first()
        if result is None:
            return {"error": "No messages received from agent yet."}
        time_diff = (datetime.now() - result.time).total_seconds()
        return {
            "last_message_time": int(result.time.timestamp()),
            "seconds_since_last_message": time_diff,
        }
