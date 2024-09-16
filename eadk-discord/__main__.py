import os

import discord
from discord import Client, Intents
from discord.message import Message

intents: Intents = discord.Intents.default()
intents.message_content = True

client: Client = discord.Client(intents=intents)

bot_token_option: str | None = os.getenv("DISCORD_BOT_TOKEN")
if bot_token_option is None:
    raise ValueError("DISCORD_BOT_TOKEN is not set in environment variables")
else:
    bot_token: str = bot_token_option


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: Message):
    print(type(message))
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")


client.run(bot_token)
