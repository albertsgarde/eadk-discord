# pragma: coverage exclude file
import logging
from datetime import date, datetime
from pathlib import Path

import discord
from beartype import beartype
from discord import Intents, Interaction, Member, app_commands
from discord.abc import Snowflake
from discord.app_commands import AppCommandError, Choice, Range
from discord.ext import commands
from discord.ext.commands import Bot, Context

from eadk_discord.bot import CommandInfo, EADKBot, Response
from eadk_discord.database import Database
from eadk_discord.database.event import Event, SetNumDesks

TEST_SERVER_ROLE_ID = 1287776907563106436
EADK_DESK_ADMIN_ID = 1288070128533114880
EADK_DESK_REGULAR_ID = 1288068945324146718

INTERNAL_ERROR_MESSAGE = "INTERNAL ERROR HAS OCCURRED BEEP BOOP"


def author_id(interaction: Interaction) -> int:
    return interaction.user.id


async def date_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    options = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return [Choice(name=option, value=option) for option in options if option.startswith(current.lower())]


async def channel_check(interaction: Interaction[discord.Client]) -> bool:
    test_server_channel_id = 1285163169391841323
    eadk_office_channel_id = 1283770439381946461
    return interaction.channel_id == test_server_channel_id or interaction.channel_id == eadk_office_channel_id


@beartype
def setup_bot(database_path: Path, guilds: list[Snowflake]) -> Bot:
    if database_path.exists():
        database = Database.load(database_path)
    else:
        database = Database.initialize(date.today())
        database.handle_event(
            Event(author=None, time=datetime.now(), event=SetNumDesks(date=date.today(), num_desks=6))
        )
    database.save(database_path)

    intents: Intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    eadk_bot = EADKBot(database)
    bot = Bot(command_prefix="!", intents=intents)

    @bot.tree.command(name="info", description="Get current booking status.", guilds=guilds)
    @app_commands.autocomplete(date_arg=date_autocomplete)
    @app_commands.rename(date_arg="date")
    @app_commands.check(channel_check)
    async def info(
        interaction: Interaction,
        date_arg: str | None,
    ) -> None:
        await eadk_bot.info(
            CommandInfo.from_interaction(interaction),
            date_arg,
        ).send(interaction)

    @bot.tree.command(name="book", description="Book a desk.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date", desk_num_arg="desk_id")
    @app_commands.check(channel_check)
    @app_commands.checks.has_any_role(TEST_SERVER_ROLE_ID, EADK_DESK_ADMIN_ID, EADK_DESK_REGULAR_ID)
    async def book(
        interaction: Interaction,
        booking_date_arg: str | None,
        user: Member | None,
        desk_num_arg: Range[int, 1] | None,
        end_date_arg: str | None,
    ) -> None:
        await eadk_bot.book(
            CommandInfo.from_interaction(interaction),
            booking_date_arg,
            user.id if user else None,
            desk_num_arg,
            end_date_arg,
        ).send(interaction)
        database.save(database_path)

    @bot.tree.command(name="unbook", description="Unbook a desk.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date", desk="desk_id")
    @app_commands.check(channel_check)
    @app_commands.checks.has_any_role(TEST_SERVER_ROLE_ID, EADK_DESK_ADMIN_ID, EADK_DESK_REGULAR_ID)
    async def unbook(
        interaction: Interaction,
        booking_date_arg: str | None,
        user: Member | None,
        desk_num_arg: Range[int, 1] | None,
        end_date_arg: str | None,
    ) -> None:
        await eadk_bot.unbook(
            CommandInfo.from_interaction(interaction),
            booking_date_arg,
            user.id if user else None,
            desk_num_arg,
            end_date_arg,
        ).send(interaction)
        database.save(database_path)

    @bot.tree.command(
        name="makeowned", description="Make a user the owner of the desk from a specific date onwards", guilds=guilds
    )
    @app_commands.autocomplete(start_date_str=date_autocomplete)
    @app_commands.rename(start_date_str="start_date", desk="desk_id")
    @app_commands.check(channel_check)
    @app_commands.checks.has_any_role(TEST_SERVER_ROLE_ID, EADK_DESK_ADMIN_ID)
    async def makeowned(
        interaction: Interaction,
        start_date_str: str,
        user: Member | None,
        desk: Range[int, 1],
    ) -> None:
        await eadk_bot.makeowned(
            CommandInfo.from_interaction(interaction), start_date_str, user.id if user else None, desk
        ).send(interaction)
        database.save(database_path)

    @bot.tree.command(
        name="makeflex", description="Make a desk a flex desk from a specific date onwards", guilds=guilds
    )
    @app_commands.autocomplete(start_date_str=date_autocomplete)
    @app_commands.rename(start_date_str="start_date", desk="desk_id")
    @app_commands.check(channel_check)
    @app_commands.checks.has_any_role(TEST_SERVER_ROLE_ID, EADK_DESK_ADMIN_ID)
    async def makeflex(interaction: Interaction, start_date_str: str, desk: Range[int, 1]) -> None:
        await eadk_bot.makeflex(CommandInfo.from_interaction(interaction), start_date_str, desk).send(interaction)
        database.save(database_path)

    @bot.command()
    @commands.is_owner()
    async def sync(ctx: Context) -> None:
        """Sync commands"""
        for guild in guilds:
            synced_commands = await ctx.bot.tree.sync(guild=guild)
            logging.info(f"Synced {synced_commands} commands to guild {guild}")

    @bot.command()
    @commands.is_owner()
    async def syncglobal(ctx: Context) -> None:
        """Sync commands"""
        synced_commands = await ctx.bot.tree.sync()
        logging.info(f"Synced {synced_commands} commands globally")

    @bot.event
    async def on_ready() -> None:
        logging.info(f"We have logged in as {bot.user}")

    @bot.tree.error
    async def on_error(interaction: Interaction, error: AppCommandError) -> None:
        try:
            await eadk_bot.handle_error(CommandInfo.from_interaction(interaction), error).send(interaction)
        except Exception:
            await Response(message=INTERNAL_ERROR_MESSAGE, ephemeral=True).send(interaction)
            raise

    return bot
