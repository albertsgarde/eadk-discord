import datetime
import os
from pathlib import Path

import discord
from discord import Client, Intents
from discord.message import Message

from eadk_discord.database import Database

intents: Intents = discord.Intents.default()
intents.message_content = True

client: Client = discord.Client(intents=intents)

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

database = Database.load_or_create(database_path, start_date=datetime.date.today(), starting_days=7, num_desks=6)
database.save(database_path)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: Message):
    print(type(message))
    if message.author == client.user:
        return

    if message.content.startswith("/book"):
        success = database.day(datetime.date.today()).book(0, message.author.name)
        if success:
            await message.channel.send(f"Succesfully booked desk 0 for {message.author.name}")
            database.save(database_path)
        else:
            await message.channel.send(
                f"Desk 0 is already booked by {database.day(datetime.date.today()).desk(0).booked_by()}"
            )


client.run(bot_token)
