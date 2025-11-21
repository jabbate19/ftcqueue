import asyncio
import websockets
import aiohttp
import configparser
from pathlib import Path
import json
from dataclasses import dataclass

@dataclass
class Config:
    inbound_host: str
    event_code: str
    outbound_host: str
    api_key: str

CONFIG_FILE = "config.ini"

async def initialize(config: Config):
    dump_url = f"http://{config.inbound_host}/api/v2/events/testevent/full/"
    init_url = f"{config.outbound_host}/api/v1/initialize"
    async with aiohttp.ClientSession() as session:
        async with session.get(dump_url) as response:
            payload = await response.json()
    team_numbers = [team["number"] for team in payload["teamList"].get("teams", [])]
    matches = [
        {
            "matchName": match["matchBrief"]["matchName"],
            "matchNumber": match["matchBrief"]["matchNumber"],
            "field": match["matchBrief"]["field"],
            "red1": match["matchBrief"]["red"]["team1"],
            "red2": match["matchBrief"]["red"]["team2"],
            "blue1": match["matchBrief"]["blue"]["team1"],
            "blue2": match["matchBrief"]["blue"]["team2"],
        } for match in payload["matchList"].get("matches", [])
    ]
    async with aiohttp.ClientSession(headers={"X-AGENT-KEY": config.api_key}) as session:
        try:
            async with session.post(init_url, json={"teams": team_numbers, "matches": matches}) as response:
                if response.status != 200:
                    print(f"POST to {init_url} gave invalid code: {response.status}")
        except Exception as e:
            print(f"Failed to fetch initial data: {e}")
            return
            

async def listen(config: Config):
    url = f"ws://{config.inbound_host}/api/v2/stream/?code={config.event_code}"
    update_url = f"{config.outbound_host}/api/v1/update"
    ping_url = f"{config.outbound_host}/api/v1/ping"
    print(f"Connecting to {url}")
    
    async with aiohttp.ClientSession(headers={"X-AGENT-KEY": config.api_key}) as session:
        try:
            async with websockets.connect(url) as websocket:
                async for message in websocket:
                    # Forward message to outbound host
                    print(message)
                    if message == "pong":
                        try:
                            async with session.post(ping_url) as resp:
                                if resp.status != 200:
                                    print(f"POST to {ping_url} gave invalid code: {resp.status}")
                        except Exception as e:
                            print(f"Failed to POST to {ping_url}: {e}")
                        finally:
                            continue
                    try:
                        async with session.post(update_url, json=json.loads(message)) as resp:
                            if resp.status != 200:
                                print(f"POST to {update_url} gave invalid code: {resp.status}")
                    except Exception as e:
                        print(f"Failed to POST to {update_url}: {e}")
        except Exception as e:
            print(f"WebSocket error: {e}")

def load_config(config_file: str = CONFIG_FILE) -> Config:
    config = configparser.ConfigParser()
    path = Path(config_file)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    config.read(config_file)
    host = config["inbound"]["host"]
    code = config["inbound"]["code"]
    outbound = config["outbound"]["host"]
    api_key = config["outbound"]["apikey"]
    return Config(host, code, outbound, api_key)

def main():
    config = load_config()
    # asyncio.run(initialize(config))
    asyncio.run(listen(config))

if __name__ == "__main__":
    main()
