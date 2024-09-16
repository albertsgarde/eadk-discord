import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from beartype import claw
from discord import Intents
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


bot = Bot(command_prefix="/", intents=intents)


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


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.command()
async def info(ctx: Context):
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
        await ctx.send(f"{available_desks_str}")
    except Exception:
        await ctx.send("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
        raise


@bot.command()
async def book(ctx: Context):
    try:
        today, booking_date = get_booking_date()
        booking_day = database.day(booking_date)
        if booking_day is None:
            raise Exception("INTERNAL ERROR: booking day not found, but today and tomorrow should always exist")
        desk_index = booking_day.get_available_desk()
        if desk_index is None:
            await ctx.send(f"No more desks are available for booking {'today' if today else 'tomorrow'}.")
            return
        else:
            desk_num = desk_index + 1
            desk = booking_day.desk(desk_index)
            success = desk.book(ctx.author.name)
            if not success:
                raise Exception(
                    f"INTERNAL ERROR: desk {desk_index} was not available, "
                    "but available_desk() returned it as available"
                )
            await ctx.send(f"Desk {desk_num} has been booked for you {'today' if today else 'tomorrow'}.")
    except Exception:
        await ctx.send("INTERNAL ERROR HAS OCCURRED BEEP BOOP")
        raise
    database.save(database_path)


bot.run(bot_token)
