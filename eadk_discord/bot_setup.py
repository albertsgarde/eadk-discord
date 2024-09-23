import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import Intents, Interaction, Member, app_commands
from discord.abc import Snowflake
from discord.app_commands import Choice, Range, Transform
from discord.ext import commands
from discord.ext.commands import Bot, Context

from eadk_discord import fmt
from eadk_discord.database import Database
from eadk_discord.date_converter import DateConverter
from eadk_discord.event import BookDesk, Event, MakeFlex, MakeOwned, SetNumDesks, UnbookDesk
from eadk_discord.state import Day, HandleEventError, State

TIME_ZONE = ZoneInfo("Europe/Copenhagen")


def format_date(date: date) -> str:
    return date.isoformat()


def get_booking_date(booking_date_arg: date | str | None) -> date | str:
    """
    Returns a tuple of two values:
    - A boolean indicating whether it is currently before 17:00.
    - A date object representing the date on which desks should be booked.
    """
    if booking_date_arg is not None:
        return booking_date_arg
    now = datetime.now(TIME_ZONE)
    booking_date = now.date() if now.hour < 17 else now.date() + timedelta(days=1)
    return booking_date


async def handle_date(
    database: State, interaction: Interaction, booking_date_arg: date | str | None
) -> tuple[date, Day] | None:
    booking_date = get_booking_date(booking_date_arg)
    if isinstance(booking_date, str):
        await interaction.response.send_message(booking_date)
        return None
    if booking_date < database.start_date:
        await interaction.response.send_message(
            f"Date {format_date(booking_date)} is not in the database. "
            f"The database starts at {format_date(database.start_date)}."
        )
        return None
    booking_day, _ = database.day(booking_date)
    if booking_day is None:
        await interaction.response.send_message(f"Date {format_date(booking_date)} is too far in the future.")
        return None
    return booking_date, booking_day


def author_id(interaction: Interaction) -> int:
    return interaction.user.id


async def date_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    options = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return [Choice(name=option, value=option) for option in options if option.startswith(current.lower())]


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

    bot = Bot(command_prefix="!", intents=intents)

    @bot.tree.command(name="info", description="Get current booking status.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date")
    async def info(
        interaction: Interaction,
        booking_date_arg: Transform[date | str, DateConverter] | None,
    ) -> None:
        try:
            handle_date_result = await handle_date(database.state, interaction, booking_date_arg)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result

            desk_numbers_str = "\n".join(str(i + 1) for i in range(len(booking_day.desks)))
            desk_bookers_str = "\n".join(
                fmt.user(interaction, desk.booker) if desk.booker else "**Free**" for desk in booking_day.desks
            )
            desk_owners_str = "\n".join(
                fmt.user(interaction, desk.owner) if desk.owner else "**Flex**" for desk in booking_day.desks
            )

            await interaction.response.send_message(
                embed=discord.Embed(title="Desk availability", description=f"{booking_date.strftime('%A %Y-%m-%d')}")
                .add_field(name="Desk", value=desk_numbers_str, inline=True)
                .add_field(name="Booked by", value=desk_bookers_str, inline=True)
                .add_field(name="Owner", value=desk_owners_str, inline=True),
                ephemeral=True,
            )
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP", ephemeral=True)
            raise

    @bot.tree.command(name="book", description="Book a desk.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date")
    @app_commands.rename(desk="desk_id")
    async def book(
        interaction: Interaction,
        booking_date_arg: Transform[date | str, DateConverter] | None,
        user: Member | None,
        desk: Range[int, 1] | None,
    ) -> None:
        try:
            handle_date_result = await handle_date(database.state, interaction, booking_date_arg)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. Desks cannot be booked in the past.", ephemeral=True
                )
                return

            if user:
                user_id = user.id
            else:
                user_id = author_id(interaction)

            if desk:
                if desk < 1 or desk > len(booking_day.desks):
                    await interaction.response.send_message(
                        f"Desk {desk} does not exist. There are only {len(booking_day.desks)} desks.", ephemeral=True
                    )
                    return
                desk_index = desk - 1
                desk_num = desk
                if booking_day.desk(desk_index).booker:
                    await interaction.response.send_message(
                        f"Desk {desk} is already booked by {booking_day.desk(desk_index).booker} on {date_str}.",
                        ephemeral=True,
                    )
                    return
            else:
                desk_index_option = booking_day.get_available_desk()
                if desk_index_option is not None:
                    desk_index = desk_index_option
                    desk_num = desk_index + 1
                else:
                    await interaction.response.send_message(
                        f"No more desks are available for booking on {date_str}.", ephemeral=True
                    )
                    return
            try:
                database.handle_event(
                    Event(
                        author=user_id,
                        time=datetime.now(),
                        event=BookDesk(date=booking_date, desk_index=desk_index, user=user_id),
                    )
                )
                await interaction.response.send_message(
                    f"Desk {desk_num} has been booked for {fmt.user(interaction, user_id)} on {date_str}."
                )
            except HandleEventError as e:
                await interaction.response.send_message(e.message(lambda id: fmt.user(interaction, id)))
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP", ephemeral=True)
            raise
        database.save(database_path)

    @bot.tree.command(name="unbook", description="Unbook a desk.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date")
    @app_commands.rename(desk="desk_id")
    async def unbook(
        interaction: Interaction,
        booking_date_arg: Transform[date | str, DateConverter] | None,
        user: Member | None,
        desk: Range[int, 1] | None,
    ) -> None:
        try:
            handle_date_result = await handle_date(database.state, interaction, booking_date_arg)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. Desks cannot be unbooked in the past.", ephemeral=True
                )
                return

            if desk is not None:
                if desk < 1 or desk > len(booking_day.desks):
                    await interaction.response.send_message(
                        f"Desk {desk} does not exist. There are only {len(booking_day.desks)} desks.", ephemeral=True
                    )
                    return
                desk_index = desk - 1
                desk_num = desk
            else:
                if user:
                    user_id = user.id
                else:
                    user_id = author_id(interaction)
                desk_indices = booking_day.booked_desks(user_id)
                if desk_indices:
                    desk_index = desk_indices[0]
                    desk_num = desk_index + 1
                else:
                    await interaction.response.send_message(
                        f"{user_id} already has no desks booked for {date_str}.", ephemeral=True
                    )
                    return

            try:
                desk_owner = booking_day.desk(desk_index).owner
                if user_id and user_id != desk_owner:
                    await interaction.response.send_message(
                        f"Desk {desk_num} is not booked by {fmt.user(interaction, user_id)} on {date_str}.",
                        ephemeral=True,
                    )
                    return
                if desk_owner:
                    database.handle_event(
                        Event(
                            author=user_id,
                            time=datetime.now(),
                            event=UnbookDesk(date=booking_date, desk_index=desk_index),
                        )
                    )
                    await interaction.response.send_message(
                        f"Desk {desk_num} is no longer booked for {fmt.user(interaction, desk_owner)} on {date_str}."
                    )
                else:
                    await interaction.response.send_message(
                        f"Desk {desk_num} is already free on {date_str}.", ephemeral=True
                    )
            except HandleEventError as e:
                await interaction.response.send_message(e.message(lambda id: fmt.user(interaction, id)))
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP", ephemeral=True)
            raise
        database.save(database_path)

    @bot.tree.command(
        name="makeowned", description="Make a user the owner of the desk from a specific date onwards", guilds=guilds
    )
    @app_commands.autocomplete(start_date=date_autocomplete)
    @app_commands.rename(desk="desk_id")
    async def makeowned(
        interaction: Interaction,
        start_date: Transform[date | str, DateConverter],
        user: Member | None,
        desk: Range[int, 1],
    ) -> None:
        try:
            handle_date_result = await handle_date(database.state, interaction, start_date)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. Desks cannot be made permanent retroactively.",
                    ephemeral=True,
                )
                return

            if desk < 1 or desk > len(booking_day.desks):
                await interaction.response.send_message(
                    f"Desk {desk} does not exist. There are only {len(booking_day.desks)} desks.", ephemeral=True
                )
                return

            desk_index = desk - 1

            if user:
                user_id = user.id
            else:
                user_id = author_id(interaction)
            try:
                database.handle_event(
                    Event(
                        author=user_id,
                        time=datetime.now(),
                        event=MakeOwned(start_date=booking_date, desk_index=desk_index, user=user_id),
                    )
                )
                await interaction.response.send_message(
                    f"Desk {desk} is now owned by {fmt.user(interaction, user_id)} from {date_str} onwards."
                )
            except HandleEventError as e:
                await interaction.response.send_message(e.message(lambda id: fmt.user(interaction, id)))
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP", ephemeral=True)
            raise
        database.save(database_path)

    @bot.tree.command(
        name="makeflex", description="Make a desk a flex desk from a specific date onwards", guilds=guilds
    )
    @app_commands.autocomplete(start_date=date_autocomplete)
    @app_commands.rename(desk="desk_id")
    async def makeflex(
        interaction: Interaction, start_date: Transform[date | str, DateConverter], desk: Range[int, 1]
    ) -> None:
        try:
            handle_date_result = await handle_date(database.state, interaction, start_date)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. You cannot make a desk permanent retroactively.",
                    ephemeral=True,
                )
                return

            if desk < 1 or desk > len(booking_day.desks):
                await interaction.response.send_message(
                    f"Desk {desk} does not exist. There are only {len(booking_day.desks)} desks.", ephemeral=True
                )
                return

            desk_index = desk - 1

            try:
                database.handle_event(
                    Event(
                        author=author_id(interaction),
                        time=datetime.now(),
                        event=MakeFlex(start_date=booking_date, desk_index=desk_index),
                    )
                )
                await interaction.response.send_message(f"Desk {desk} is now a flex desk from {date_str} onwards.")
            except HandleEventError as e:
                await interaction.response.send_message(e.message(lambda id: fmt.user(interaction, id)))
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP", ephemeral=True)
            raise
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
    async def on_ready():
        logging.info(f"We have logged in as {bot.user}")

    return bot
