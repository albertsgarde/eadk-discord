from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import Intents, Interaction, Member, app_commands
from discord.abc import Snowflake
from discord.app_commands import Choice, Range, Transform
from discord.ext import commands
from discord.ext.commands import Bot, Context

from eadk_discord.database import Database, Day, DeskAlreadyOwnedError
from eadk_discord.date_converter import DateConverter

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
    database: Database, interaction: Interaction, booking_date_arg: date | str | None
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
    booking_day = database.day(booking_date)
    if booking_day is None:
        await interaction.response.send_message(f"Date {format_date(booking_date)} is too far in the future.")
        return None
    return booking_date, booking_day


def author_name(interaction: Interaction) -> str:
    return interaction.user.display_name


async def date_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    options = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return [Choice(name=option, value=option) for option in options if option.startswith(current.lower())]


def setup_bot(database_path: Path, guilds: list[Snowflake]) -> Bot:
    database = Database.load_or_create(database_path, start_date=date.today(), starting_days=7, num_desks=6)
    database.save(database_path)

    intents: Intents = discord.Intents.default()
    intents.message_content = True

    bot = Bot(command_prefix="!", intents=intents)

    @bot.tree.command(name="info", description="Get available desks for today or tomorrow.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date")
    async def info(
        interaction: Interaction,
        booking_date_arg: Transform[date | str, DateConverter] | None,
        user: Member | None,
    ) -> None:
        try:
            handle_date_result = await handle_date(database, interaction, booking_date_arg)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result

            date_str = format_date(booking_date)
            available_desks = booking_day.available_desks()
            available_desks_str = (
                f"Available desks {date_str}: " f"{', '.join(str(desk + 1) for desk in available_desks)}"
                if available_desks
                else f"No desks are available {date_str}."
            )

            if user:
                user_name = user.display_name
            else:
                user_name = author_name(interaction)
            booked_desks = booking_day.booked_desks(user_name)
            if len(booked_desks) == 1:
                booked_desk = booked_desks[0]
                booked_desk_num = booked_desk + 1
                booked_desks_str = f"\nDesk {booked_desk_num} is booked for {user_name}."
            elif len(booked_desks) > 1:
                desk_nums_str = ", ".join(str(desk + 1) for desk in booked_desks)
                booked_desks_str = f"\nDesks {desk_nums_str} are booked for {user_name}."
            else:
                booked_desks_str = ""

            await interaction.response.send_message(f"{available_desks_str}{booked_desks_str}")
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
            raise

    @bot.tree.command(name="book", description="Book a desk for today or tomorrow.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date")
    async def book(
        interaction: Interaction,
        booking_date_arg: Transform[date | str, DateConverter] | None,
        user: Member | None,
    ) -> None:
        try:
            handle_date_result = await handle_date(database, interaction, booking_date_arg)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. Desks cannot be booked in the past."
                )
                return

            if user:
                user_name = user.display_name
            else:
                user_name = author_name(interaction)
            desk_index = booking_day.get_available_desk()
            if desk_index is None:
                await interaction.response.send_message(f"No more desks are available for booking {date_str}.")
                return
            else:
                desk_num = desk_index + 1
                desk = booking_day.desk(desk_index)
                success = desk.book(user_name)
                if not success:
                    raise Exception(
                        f"INTERNAL ERROR: desk {desk_index} was not available, "
                        "but available_desk() returned it as available"
                    )
                await interaction.response.send_message(f"Desk {desk_num} has been booked for {user_name} {date_str}.")
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
            raise
        database.save(database_path)

    @bot.tree.command(name="unbook", description="Unbook a desk for today or tomorrow.", guilds=guilds)
    @app_commands.autocomplete(booking_date_arg=date_autocomplete)
    @app_commands.rename(booking_date_arg="date")
    async def unbook(
        interaction: Interaction,
        booking_date_arg: Transform[date | str, DateConverter] | None,
        user: Member | None,
    ) -> None:
        try:
            handle_date_result = await handle_date(database, interaction, booking_date_arg)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. Desks cannot be unbooked in the past."
                )
                return

            if user:
                user_name = user.display_name
            else:
                user_name = author_name(interaction)
            desk_indices = booking_day.booked_desks(user_name)
            if desk_indices:
                desk_index = desk_indices[0]
                desk_num = desk_index + 1
                booking_day.desk(desk_index).unbook()
                await interaction.response.send_message(
                    f"Desk {desk_num} is no longer booked for {user_name} {date_str}."
                )
            else:
                await interaction.response.send_message(f"{user_name} already has no desks booked for {date_str}.")
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
            raise
        database.save(database_path)

    @bot.tree.command(
        name="makeowned", description="Make a user the owner of the desk from a specific date", guilds=guilds
    )
    @app_commands.autocomplete(start_date=date_autocomplete)
    async def makeowned(
        interaction: Interaction,
        start_date: Transform[date | str, DateConverter],
        user: Member | None,
        desk: Range[int, 1],
    ) -> None:
        try:
            handle_date_result = await handle_date(database, interaction, start_date)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. Desks cannot be made permanent retroactively."
                )
                return

            if desk < 1 or desk > len(booking_day.desks):
                await interaction.response.send_message(
                    f"Desk {desk} does not exist. There are only {len(booking_day.desks)} desks."
                )
                return

            desk_index = desk - 1

            if user:
                user_name = user.display_name
            else:
                user_name = author_name(interaction)
            try:
                database.make_owned(booking_date, desk_index, user_name)
                await interaction.response.send_message(
                    f"Desk {desk} is now owned by {user_name} from {date_str} onwards."
                )
            except DeskAlreadyOwnedError as e:
                await interaction.response.send_message(f"Desk {e.desk + 1} is already owned by {e.owner} on {e.day}.")
                return
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
            raise
        database.save(database_path)

    @bot.tree.command(name="makeflex", description="Make a desk a flex desk from a specific date", guilds=guilds)
    @app_commands.autocomplete(start_date=date_autocomplete)
    async def makeflex(
        interaction: Interaction, start_date: Transform[date | str, DateConverter], desk: Range[int, 1]
    ) -> None:
        try:
            handle_date_result = await handle_date(database, interaction, start_date)
            if handle_date_result is None:
                return
            booking_date, booking_day = handle_date_result
            date_str = format_date(booking_date)

            if booking_date < date.today():
                await interaction.response.send_message(
                    f"Date {date_str} not available for booking. You cannot make a desk permanent retroactively."
                )
                return

            if desk < 1 or desk > len(booking_day.desks):
                await interaction.response.send_message(
                    f"Desk {desk} does not exist. There are only {len(booking_day.desks)} desks."
                )
                return

            desk_index = desk - 1

            database.make_flex(booking_date, desk_index)
            await interaction.response.send_message(f"Desk {desk} is now a flex desk from {date_str} onwards.")
        except Exception:
            await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
            raise
        database.save(database_path)

    @bot.command()
    @commands.is_owner()
    async def sync(ctx: Context) -> None:
        """Sync commands"""
        for guild in guilds:
            synced_commands = await ctx.bot.tree.sync(guild=guild)
            print(f"Synced {synced_commands} commands to guild {guild}")

    @bot.event
    async def on_ready():
        print(f"We have logged in as {bot.user}")

    return bot
