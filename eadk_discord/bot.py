from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from beartype import beartype
from discord.app_commands import AppCommandError
from pydantic import BaseModel, Field

from eadk_discord import dates, fmt
from eadk_discord.database import Database
from eadk_discord.database.event import BookDesk, Event, MakeFlex, MakeOwned, UnbookDesk
from eadk_discord.database.event_errors import EventError

TIME_ZONE = ZoneInfo("Europe/Copenhagen")


class CommandInfo(BaseModel):
    now: datetime = Field()
    format_user: Callable[[int], str] = Field()
    author_id: int = Field()

    @beartype
    @staticmethod
    def from_interaction(interaction: discord.Interaction) -> "CommandInfo":
        return CommandInfo(
            now=datetime.now(TIME_ZONE),
            format_user=lambda user: fmt.user(interaction, user),
            author_id=interaction.user.id,
        )


@dataclass
class Response:
    message: str
    ephemeral: bool
    embed: discord.Embed | None

    @beartype
    def __init__(self, message: str = "", ephemeral: bool = False, embed: discord.Embed | None = None) -> None:
        self.message = message
        self.ephemeral = ephemeral
        self.embed = embed

    @beartype
    async def send(self, interaction: discord.Interaction) -> None:
        if self.embed is None:
            await interaction.response.send_message(self.message, ephemeral=self.ephemeral)
        else:
            await interaction.response.send_message(self.message, ephemeral=self.ephemeral, embed=self.embed)


class EADKBot:
    _database: Database

    @beartype
    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def database(self) -> Database:
        return self._database

    @beartype
    def info(self, info: CommandInfo, date_str: str | None) -> Response:
        booking_date = dates.get_booking_date(date_str, info.now)
        booking_day, _ = self._database.state.day(booking_date)

        desk_numbers_str = "\n".join(str(i + 1) for i in range(len(booking_day.desks)))
        desk_bookers_str = "\n".join(
            info.format_user(desk.booker) if desk.booker else "**Free**" for desk in booking_day.desks
        )
        desk_owners_str = "\n".join(
            info.format_user(desk.owner) if desk.owner else "**Flex**" for desk in booking_day.desks
        )

        return Response(
            message="",
            ephemeral=True,
            embed=discord.Embed(title="Desk availability", description=f"{booking_date.strftime('%A %Y-%m-%d')}")
            .add_field(name="Desk", value=desk_numbers_str, inline=True)
            .add_field(name="Booked by", value=desk_bookers_str, inline=True)
            .add_field(name="Owner", value=desk_owners_str, inline=True),
        )

    @beartype
    def book(self, info: CommandInfo, date_str: str | None, user_id: int | None, desk_num: int | None) -> Response:
        if user_id is None:
            user_id = info.author_id

        booking_date = dates.get_booking_date(date_str, info.now)
        booking_day, _ = self._database.state.day(booking_date)
        date_str = fmt.date(booking_date)

        if booking_date < info.now.date():
            return Response(
                message=f"Date {date_str} not available for booking. Desks cannot be unbooked in the past.",
                ephemeral=True,
            )

        if desk_num is not None:
            desk_index = desk_num - 1
        else:
            desk_index_option = booking_day.get_available_desk()
            if desk_index_option is not None:
                desk_index = desk_index_option
                desk_num = desk_index + 1
            else:
                return Response(message=f"No more desks are available for booking on {date_str}.", ephemeral=True)
        self._database.handle_event(
            Event(
                author=info.author_id,
                time=datetime.now(),
                event=BookDesk(date=booking_date, desk_index=desk_index, user=user_id),
            )
        )
        return Response(message=f"Desk {desk_num} has been booked for {info.format_user(user_id)} on {date_str}.")

    @beartype
    def unbook(self, info: CommandInfo, date_str: str | None, user_id: int | None, desk_num: int | None) -> Response:
        booking_date = dates.get_booking_date(date_str, info.now)
        booking_day, _ = self._database.state.day(booking_date)
        date_str = fmt.date(booking_date)

        if booking_date < info.now.date():
            return Response(
                message=f"Date {date_str} not available for booking. Desks cannot be unbooked in the past.",
                ephemeral=True,
            )

        if desk_num is not None:
            desk_index = desk_num - 1
            if user_id is not None:
                if user_id != booking_day.desk(desk_index).booker:
                    return Response(
                        message=f"Desk {desk_num} is not booked by {info.format_user(user_id)} on {date_str}.",
                        ephemeral=True,
                    )
        else:
            if user_id is None:
                user_id = info.author_id
            desk_indices = booking_day.booked_desks(user_id)
            if desk_indices:
                desk_index = desk_indices[0]
                desk_num = desk_index + 1
            else:
                return Response(
                    message=f"{info.format_user(user_id)} already has no desks booked for {date_str}.", ephemeral=True
                )

        desk_booker = booking_day.desk(desk_index).booker
        if desk_booker is not None:
            self._database.handle_event(
                Event(
                    author=info.author_id,
                    time=datetime.now(),
                    event=UnbookDesk(date=booking_date, desk_index=desk_index),
                )
            )
            return Response(
                message=f"Desk {desk_num} is no longer booked for {info.format_user(desk_booker)} on {date_str}."
            )
        else:
            return Response(message=f"Desk {desk_num} is already free on {date_str}.", ephemeral=True)

    @beartype
    def makeowned(self, info: CommandInfo, start_date_str: str, user_id: int | None, desk_num: int) -> Response:
        booking_date = dates.get_booking_date(start_date_str, info.now)
        date_str = fmt.date(booking_date)

        if booking_date < info.now.date():
            return Response(
                message=f"Date {date_str} not available for booking. Desks cannot be made permanent retroactively.",
                ephemeral=True,
            )

        desk_index = desk_num - 1

        if user_id is None:
            user_id = info.author_id
        self._database.handle_event(
            Event(
                author=info.author_id,
                time=datetime.now(),
                event=MakeOwned(start_date=booking_date, desk_index=desk_index, user=user_id),
            )
        )
        return Response(message=f"Desk {desk_num} is now owned by {info.format_user(user_id)} from {date_str} onwards.")

    @beartype
    def makeflex(self, info: CommandInfo, start_date_str: str, desk_num: int) -> Response:
        booking_date = dates.get_booking_date(start_date_str, info.now)
        date_str = fmt.date(booking_date)

        if booking_date < info.now.date():
            return Response(
                message=f"Date {date_str} not available for booking. You cannot make a desk permanent retroactively.",
                ephemeral=True,
            )

        desk_index = desk_num - 1

        self._database.handle_event(
            Event(
                author=info.author_id,
                time=datetime.now(),
                event=MakeFlex(start_date=booking_date, desk_index=desk_index),
            )
        )
        return Response(message=f"Desk {desk_num} is now a flex desk from {date_str} onwards.")

    @beartype
    def handle_error(self, info: CommandInfo, error: AppCommandError) -> Response:
        match error:
            case discord.app_commands.errors.MissingAnyRole() | discord.app_commands.errors.MissingRole():
                return Response(message="You do not have permission to run this command.", ephemeral=True)
            case discord.app_commands.errors.CheckFailure():
                return Response(message="This command can only be used in the office channel.", ephemeral=True)
            case discord.app_commands.errors.CommandInvokeError() as error:
                match error.__cause__:
                    case EventError() as event_error:
                        return Response(message=event_error.message(info.format_user), ephemeral=True)
        raise error
