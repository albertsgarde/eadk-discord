import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from beartype import claw
from discord import Intents, Interaction
from discord.ext import commands
from discord.ext.commands import Bot, Context

from eadk_discord.database import Database

claw.beartype_this_package()

TIME_ZONE = ZoneInfo("Europe/Copenhagen")

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

database = Database.load_or_create(database_path, start_date=date.today(), starting_days=7, num_desks=6)
database.save(database_path)


intents: Intents = discord.Intents.default()
intents.message_content = True


bot = Bot(command_prefix="!", intents=intents)


def get_booking_date() -> tuple[bool, date]:
    """
    Returns a tuple of two values:
    - A boolean indicating whether it is currently before 17:00.
    - A date object representing the date on which desks should be booked.
    """
    now = datetime.now(TIME_ZONE)
    today = now.hour < 17
    booking_date = now.date() if now.hour < 17 else now.date() + timedelta(days=1)
    return today, booking_date


def author_name(interaction: Interaction) -> str:
    return interaction.user.display_name


@bot.tree.command(name="info", description="Get available desks for today or tomorrow.")
async def info(
    interaction: Interaction,
) -> None:
    try:
        today, booking_date = get_booking_date()
        booking_day = database.day(booking_date)
        if booking_day is None:
            raise Exception("INTERNAL ERROR: booking day not found, but today and tomorrow should always exist")
        available_desks = booking_day.available_desks()
        available_desks_str = (
            f"Available desks {'today' if today else 'tomorrow'}: "
            f"{', '.join(str(desk + 1) for desk in available_desks)}"
            if available_desks
            else f"No desks are available {'today' if today else 'tomorrow'}."
        )

        member = author_name(interaction)
        booked_desks = booking_day.booked_desks(member)
        if len(booked_desks) == 1:
            booked_desk = booked_desks[0]
            booked_desk_num = booked_desk + 1
            booked_desks_str = f"\nDesk {booked_desk_num} is booked for you {'today' if today else 'tomorrow'}."
        elif len(booked_desks) > 1:
            desk_nums_str = ", ".join(str(desk + 1) for desk in booked_desks)
            booked_desks_str = f"\nDesks {desk_nums_str} are booked for you {'today' if today else 'tomorrow'}."
        else:
            booked_desks_str = ""

        await interaction.response.send_message(f"{available_desks_str}{booked_desks_str}")
    except Exception:
        await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
        raise


@bot.tree.command(name="book", description="Book a desk for today or tomorrow.")
async def book(
    interaction: Interaction,
) -> None:
    try:
        today, booking_date = get_booking_date()
        booking_day = database.day(booking_date)
        if booking_day is None:
            raise Exception("INTERNAL ERROR: booking day not found, but today and tomorrow should always exist")
        desk_index = booking_day.get_available_desk()
        if desk_index is None:
            await interaction.response.send_message(
                f"No more desks are available for booking {'today' if today else 'tomorrow'}."
            )
            return
        else:
            desk_num = desk_index + 1
            desk = booking_day.desk(desk_index)
            success = desk.book(author_name(interaction))
            if not success:
                raise Exception(
                    f"INTERNAL ERROR: desk {desk_index} was not available, "
                    "but available_desk() returned it as available"
                )
            await interaction.response.send_message(
                f"Desk {desk_num} has been booked for you {'today' if today else 'tomorrow'}."
            )
    except Exception:
        await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
        raise
    database.save(database_path)


@bot.tree.command(name="unbook", description="Unbook a desk for today or tomorrow.")
async def unbook(
    interaction: Interaction,
) -> None:
    try:
        today, booking_date = get_booking_date()
        booking_day = database.day(booking_date)
        if booking_day is None:
            raise Exception("INTERNAL ERROR: booking day not found, but today and tomorrow should always exist")
        author = author_name(interaction)
        desk_indices = booking_day.booked_desks(author)
        if desk_indices:
            desk_index = desk_indices[0]
            desk_num = desk_index + 1
            booking_day.desk(desk_index).unbook()
            await interaction.response.send_message(
                f"Desk {desk_num} is no longer booked for you {'today' if today else 'tomorrow'}."
            )
        else:
            await interaction.response.send_message(
                f"You already have no desks booked for {'today' if today else 'tomorrow'}."
            )
    except Exception:
        await interaction.response.send_message("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
        raise
    database.save(database_path)


@bot.command()
@commands.is_owner()
async def sync(ctx: Context) -> None:
    """Sync commands"""
    guild = discord.Object(id=1285163168930336769)
    ctx.bot.tree.copy_global_to(guild=guild)
    ctx.bot.tree.clear_commands(guild=None)
    await ctx.bot.tree.sync(guild=None)
    synced_commands = await ctx.bot.tree.sync(guild=guild)
    print(f"Synced {synced_commands} commands to guild {guild}")


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


bot.run(bot_token)
