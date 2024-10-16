# pragma: coverage exclude file
import logging
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

import discord
from discord import Intents, Interaction, Member, app_commands
from discord.abc import Snowflake
from discord.app_commands import AppCommandError, Choice, Range
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pydantic import BaseModel

from eadk_discord.bot import CommandInfo, EADKBot, Response
from eadk_discord.database import Database
from eadk_discord.database.event import Event, SetNumDesks

INTERNAL_ERROR_MESSAGE = "INTERNAL ERROR HAS OCCURRED BEEP BOOP"


def author_id(interaction: Interaction) -> int:
    return interaction.user.id


async def date_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    options = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return [Choice(name=option, value=option) for option in options if option.startswith(current.lower())]


class BotConfig(BaseModel):
    bot_token: str
    database_path: Path
    guild_ids: Sequence[int | str]
    channel_ids: Sequence[int | str]
    regular_role_ids: Sequence[int | str]
    admin_role_ids: Sequence[int | str]

    def guilds(self) -> Sequence[Snowflake]:
        return [discord.Object(id=int(guild_id)) for guild_id in self.guild_ids]

    def setup_bot(self) -> Bot:
        database_path = self.database_path
        guilds = self.guilds()
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

        async def channel_check(interaction: Interaction[discord.Client]) -> bool:
            return interaction.channel_id in self.channel_ids

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
        @app_commands.rename(booking_date_arg="date", desk_num_arg="desk_id", end_date_arg="end_date")
        @app_commands.check(channel_check)
        @app_commands.checks.has_any_role(*self.regular_role_ids, *self.admin_role_ids)
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
        @app_commands.rename(booking_date_arg="date", desk_num_arg="desk_id", end_date_arg="end_date")
        @app_commands.check(channel_check)
        @app_commands.checks.has_any_role(*self.regular_role_ids, *self.admin_role_ids)
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
            name="makeowned",
            description="Make a user the owner of the desk from a specific date onwards",
            guilds=guilds,
        )
        @app_commands.autocomplete(start_date_str=date_autocomplete)
        @app_commands.rename(start_date_str="start_date", desk="desk_id")
        @app_commands.check(channel_check)
        @app_commands.checks.has_any_role(*self.admin_role_ids)
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
        @app_commands.checks.has_any_role(*self.admin_role_ids)
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

    def run_bot(self) -> Bot:
        bot = self.setup_bot()
        bot.run(self.bot_token)
        return bot
