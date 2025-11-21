from os import environ as env

DISCORD_TOKEN: str = env.get("DISCORD_TOKEN", "your-discord-token-here")
DISCORD_APPLICATION_ID: int = int(
    env.get("DISCORD_APPLICATION_ID", "123456789012345678")
)
DISCORD_PUBLIC_KEY: str = env.get("DISCORD_PUBLIC_KEY", "your-discord-public-key-here")
DISCORD_API_ENDPOINT: str = env.get(
    "DISCORD_API_ENDPOINT", "https://your-discord-endpoint-here"
)
DISCORD_SERVER_ID: int = int(env.get("DISCORD_SERVER_ID", "123456789012345678"))
DISCORD_NOTIFICATION_CHANNEL_ID: int = int(
    env.get("DISCORD_NOTIFICATION_CHANNEL_ID", "123456789012345678")
)

AGENT_API_KEY: str = env.get("AGENT_API_KEY", "supersecretagentapikey")
ADMIN_API_KEY: str = env.get("ADMIN_API_KEY", "supersecretadminapikey")
SQL_URI: str = env.get("SQL_URI", "sqlite:///database.db")
