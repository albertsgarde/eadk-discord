# pragma: coverage exclude file
import logging
import os
from pathlib import Path

import discord
from discord.abc import Snowflake

from eadk_discord import bot_setup

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    bot_token_option: str | None = os.getenv("DISCORD_BOT_TOKEN")
    if bot_token_option is None:
        raise ValueError("DISCORD_BOT_TOKEN is not set in environment variables")
    else:
        bot_token: str = bot_token_option

    database_path_option: str | None = os.getenv("DATABASE_PATH")
    if database_path_option is None:
        raise ValueError("DATABASE_PATH is not set in environment variables")
    else:
        database_path: Path = Path(database_path_option)

    guild_ids_option: str | None = os.getenv("GUILD_IDS")
    if guild_ids_option is None:
        raise ValueError("GUILD_IDS is not set in environment variables")
    else:
        guilds: list[Snowflake] = [discord.Object(id=int(guild_id)) for guild_id in guild_ids_option.split(",")]

    bot = bot_setup.setup_bot(database_path, guilds)

    bot.run(bot_token)
