from nacl.signing import VerifyKey
from .models import Team
import requests
from time import sleep
from random import randint
from pydantic import Json
from sqlmodel import Session
from . import config
import logging
from starlette.datastructures import Headers

DISCORD_API_BASE = "https://discord.com/api/v10"


def verify_signature(body: str, headers: Headers):
    """Verify that the request came from Discord"""
    logging.debug("Starting signature verification")
    try:
        signature = headers["x-signature-ed25519"]
        timestamp = headers["x-signature-timestamp"]

        logging.debug("Got signature, timestamp and body")
        verify_key = VerifyKey(bytes.fromhex(config.DISCORD_PUBLIC_KEY))
        logging.debug("Attempting to verify signature")
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        logging.info("Signature verified successfully")
        return True
    except Exception as e:
        logging.error(f"Bad signature error: {e}")
        return False


def get_discord_api_headers() -> dict[str, str]:
    return {
        "User-Agent": f"DiscordBot ({config.DISCORD_API_ENDPOINT}, v0.1.0)",
        "Authorization": f"Bot {config.DISCORD_TOKEN}",
    }


def register_global_commands() -> dict[str, Json]:
    set_resp = requests.post(
        f"{DISCORD_API_BASE}/applications/{config.DISCORD_APPLICATION_ID}/commands",
        json={
            "name": "setteam",
            "description": "Set your team number for role assignment",
            "options": [
                {
                    "type": 4,
                    "name": "teamnumber",
                    "description": "Your FTC team number",
                    "required": True,
                    "min_value": 1,
                    "max_value": 99999,
                }
            ],
            "type": 1,
        },
        headers=get_discord_api_headers(),
    )
    # Rate limit
    sleep(1)
    unset_resp = requests.post(
        f"{DISCORD_API_BASE}/applications/{config.DISCORD_APPLICATION_ID}/commands",
        json={
            "name": "unsetteam",
            "description": "Unset your team number for role assignment",
            "options": [
                {
                    "type": 4,
                    "name": "teamnumber",
                    "description": "Your FTC team number",
                    "required": True,
                    "min_value": 1,
                    "max_value": 99999,
                }
            ],
            "type": 1,
        },
        headers=get_discord_api_headers(),
    )
    return {
        "setteam": {
            "status_code": set_resp.status_code,
            "response": set_resp.text,
        },
        "unsetteam": {
            "status_code": unset_resp.status_code,
            "response": unset_resp.text,
        },
    }


def get_global_commands() -> requests.Response:
    return requests.get(
        f"{DISCORD_API_BASE}/applications/{config.DISCORD_APPLICATION_ID}/commands",
        headers=get_discord_api_headers(),
    )


def create_team_role(team_number: int) -> int:
    """
    Creates Role on Discord for Given Team Number. Random Color Assigned.

    Returns Role ID.
    """
    resp = requests.post(
        f"{DISCORD_API_BASE}/guilds/{config.DISCORD_SERVER_ID}/roles",
        json={
            "name": f"Team {team_number}",
            "permissions": "0",
            "mentionable": True,
            "hoist": False,
            "colors": {"primary_color": randint(0, 0xFFFFFF)},
        },
        headers=get_discord_api_headers(),
    )
    if resp.status_code != 200:
        raise Exception("Failed to create role")
    return resp.json()["id"]


def set_team(session: Session, team_number: int, user_id: int) -> dict[str, Json]:
    team = session.get(Team, team_number)
    if team is None:
        return {
            "type": 4,
            "data": {
                "tts": False,
                "content": "Error: Team Not Registered! Please contact FTA.",
                "embeds": [],
                "allowed_mentions": {"parse": []},
            },
        }
    resp = requests.put(
        f"{DISCORD_API_BASE}/guilds/{config.DISCORD_SERVER_ID}/members/{user_id}/roles/{team.discord_role_id}",
        headers=get_discord_api_headers(),
    )
    if resp.status_code != 204:
        logging.error("SET_TEAM FAIL")
        return {
            "type": 4,
            "data": {
                "tts": False,
                "content": "Error: Failed to assign role! If this continues, please contact FTA.",
                "embeds": [],
                "allowed_mentions": {"parse": []},
            },
        }
    return {
        "type": 4,
        "data": {
            "tts": False,
            "content": "Role Added!",
            "embeds": [],
            "allowed_mentions": {"parse": []},
        },
    }


def unset_team(session: Session, team_number: int, user_id: int) -> dict[str, Json]:
    team = session.get(Team, team_number)
    if team is None:
        return {
            "type": 4,
            "data": {
                "tts": False,
                "content": "Error: Team Not Registered! Please contact FTA.",
                "embeds": [],
                "allowed_mentions": {"parse": []},
            },
        }
    resp = requests.delete(
        f"{DISCORD_API_BASE}/guilds/{config.DISCORD_SERVER_ID}/members/{user_id}/roles/{team.discord_role_id}",
        headers=get_discord_api_headers(),
    )
    if resp.status_code != 204:
        return {
            "type": 4,
            "data": {
                "tts": False,
                "content": "Error: Failed to remove role! If this continues, please contact FTA.",
                "embeds": [],
                "allowed_mentions": {"parse": []},
            },
        }
    return {
        "type": 4,
        "data": {
            "tts": False,
            "content": "Role Removed!",
            "embeds": [],
            "allowed_mentions": {"parse": []},
        },
    }


def get_role_ping(role_id: int) -> str:
    return f"<@&{role_id}>"


def send_message(content: str) -> requests.Response:
    return requests.post(
        f"{DISCORD_API_BASE}/channels/{config.DISCORD_NOTIFICATION_CHANNEL_ID}/messages",
        json={"content": content, "tts": False},
        headers=get_discord_api_headers(),
    )


def parse_command(session: Session, payload: dict[str, Json]) -> dict[str, Json]:
    user_id = int(
        payload["member"]["user"]["id"]
        if "member" in payload
        else payload["user"]["id"]
    )
    match payload["data"]["name"]:
        case "setteam":
            team_number = int(
                [
                    option["value"]
                    for option in payload["data"]["options"]
                    if option["name"] == "teamnumber"
                ][0]
            )
            return set_team(session, team_number, user_id)
        case "unsetteam":
            team_number = int(
                [
                    option["value"]
                    for option in payload["data"]["options"]
                    if option["name"] == "teamnumber"
                ][0]
            )
            return unset_team(session, team_number, user_id)
        case _:
            return {
                "type": 4,
                "data": {
                    "tts": False,
                    "content": "Error: Command Not Implemented",
                    "embeds": [],
                    "allowed_mentions": {"parse": []},
                },
            }
