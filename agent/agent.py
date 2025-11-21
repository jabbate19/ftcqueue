import asyncio
import websockets
import aiohttp
import configparser
from pathlib import Path
import json

CONFIG_FILE = "config.ini"

async def listen(inbound_host: str, code: str, outbound_host: str):
    url = f"ws://{inbound_host}/api/v2/stream/?code={code}"
    outbound_url = f"https://{outbound_host}/api/v1/update"
    print(f"Connecting to {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with websockets.connect(url) as websocket:
                async for message in websocket:
                    # Forward message to outbound host
                    try:
                        async with session.post(outbound_url, json=json.loads(message)) as resp:
                            if resp.status != 200:
                                print(f"POST to {outbound_url} gave invalid code: {resp.status}")
                    except Exception as e:
                        print(f"Failed to POST to {outbound_url}: {e}")
        except Exception as e:
            print(f"WebSocket error: {e}")

def load_config(config_file: str = CONFIG_FILE):
    config = configparser.ConfigParser()
    path = Path(config_file)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    config.read(config_file)
    host = config["inbound"]["host"]
    code = config["inbound"]["code"]
    outbound = config["outbound"]["host"]
    return host, code, outbound

def main():
    host, code, outbound = load_config()
    asyncio.run(listen(host, code, outbound))

if __name__ == "__main__":
    main()
