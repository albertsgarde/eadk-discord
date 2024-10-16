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
    author_role_ids: set[int] = Field()

    @beartype
    @staticmethod
    def from_interaction(interaction: discord.Interaction) -> "CommandInfo":
        match interaction.user:
            case discord.Member() as member:
                role_ids = set(role.id for role in member.roles)
            case discord.User():
                role_ids = set()
            case _:
                raise ValueError("Invalid interaction user type")
        return CommandInfo(
            now=datetime.now(TIME_ZONE),
            format_user=lambda user: fmt.user(interaction, user),
            author_id=interaction.user.id,
            author_role_ids=role_ids,
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
    async def send(self, interaction: discord.Interaction) -> None:  # pragma: no cover
        if self.embed is None:
            await interaction.response.send_message(self.message, ephemeral=self.ephemeral)
        else:
            await interaction.response.send_message(self.message, ephemeral=self.ephemeral, embed=self.embed)


class EADKBot:
    _database: Database
    _regular_role_ids: set[int]
    _admin_role_ids: set[int]

    @beartype
    def __init__(self, database: Database, regular_role_ids: set[int], admin_role_ids: set[int]) -> None:
        self._database = database
        self._regular_role_ids = regular_role_ids
        self._admin_role_ids = admin_role_ids

    def _is_author_regular(self, info: CommandInfo) -> bool:
        return bool(info.author_role_ids.intersection(self._regular_role_ids.union(self._admin_role_ids)))

    def _is_author_admin(self, info: CommandInfo) -> bool:
        return bool(info.author_role_ids.intersection(self._admin_role_ids))

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
    def book(
        self,
        info: CommandInfo,
        date_str: str | None,
        user_id: int | None,
        desk_num: int | None,
        end_date_str: str | None,
    ) -> Response:
        if user_id is None:
            user_id = info.author_id

        booking_date = dates.get_booking_date(date_str, info.now)
        booking_day, _ = self._database.state.day(booking_date)
        date_str = fmt.date(booking_date)

        end_date = dates.parse_date_arg(end_date_str, info.now.date()) if end_date_str is not None else None

        if booking_date < info.now.date():
            return Response(
                message=f"Date {date_str} not available for booking. Desks cannot be unbooked in the past.",
                ephemeral=True,
            )

        if desk_num is not None:
            desk_index = desk_num - 1
        else:
            if end_date is not None:
                return Response(message="A desk must be specified for range bookings.", ephemeral=True)
            desk_index_option = booking_day.get_available_desk()
            if desk_index_option is not None:
                desk_index = desk_index_option
                desk_num = desk_index + 1
            else:
                return Response(message=f"No more desks are available for booking on {date_str}.", ephemeral=True)

        if end_date is not None:
            days = self._database.state.day_range(booking_date, end_date)
            for day in days:
                if day.desk(desk_index).owner is not info.author_id and not self._is_author_admin(info):
                    return Response(
                        message="Range bookings are only allowed for desks you own for the entire range.",
                        ephemeral=True,
                    )

        if user_id != info.author_id and not self._is_author_regular(info):
            return Response(message="You do not have permission to book desks for other users.", ephemeral=True)

        self._database.handle_event(
            Event(
                author=info.author_id,
                time=datetime.now(),
                event=BookDesk(
                    start_date=booking_date, end_date=end_date or booking_date, desk_index=desk_index, user=user_id
                ),
            )
        )
        if end_date is not None:
            return Response(
                message=f"Desk {desk_num} has been booked for {info.format_user(user_id)} "
                f"from {date_str} to {fmt.date(end_date)}."
            )
        else:
            return Response(message=f"Desk {desk_num} has been booked for {info.format_user(user_id)} on {date_str}.")

    @beartype
    def unbook(
        self,
        info: CommandInfo,
        date_str: str | None,
        user_id: int | None,
        desk_num: int | None,
        end_date_str: str | None,
    ) -> Response:
        booking_date = dates.get_booking_date(date_str, info.now)
        date_str = fmt.date(booking_date)

        end_date = dates.parse_date_arg(end_date_str, info.now.date()) if end_date_str is not None else booking_date

        booking_days = self._database.state.day_range(booking_date, end_date)

        if booking_date < info.now.date():
            return Response(
                message=f"Date {date_str} not available for booking. Desks cannot be unbooked in the past.",
                ephemeral=True,
            )

        if len(booking_days) > 1:
            if desk_num is None:
                return Response(message="A desk must be specified for range unbookings.", ephemeral=True)
            desk_index = desk_num - 1
            for booking_day in booking_days:
                if booking_day.desk(desk_index).owner != info.author_id and not self._is_author_admin(info):
                    return Response(
                        message="Range unbookings are only allowed for desks you own for the entire range.",
                        ephemeral=True,
                    )

        if desk_num is not None:
            desk_index = desk_num - 1
            if user_id is not None:
                for booking_day in booking_days:
                    if user_id != booking_day.desk(desk_index).booker:
                        return Response(
                            message=f"Desk {desk_num} is not booked by {info.format_user(user_id)} on {date_str}.",
                            ephemeral=True,
                        )
        else:
            assert len(booking_days) == 1
            booking_day = booking_days[0]
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

        if user_id != info.author_id and not self._is_author_regular(info):
            return Response(message="You do not have permission to unbook desks for other users.", ephemeral=True)

        if len(booking_days) > 1:
            self._database.handle_event(
                Event(
                    author=info.author_id,
                    time=datetime.now(),
                    event=UnbookDesk(start_date=booking_date, end_date=end_date, desk_index=desk_index),
                )
            )
            return Response(message=(f"Desk {desk_num} has been unbooked from {date_str} to {fmt.date(end_date)}."))
        else:
            [booking_day] = booking_days
            desk_booker = booking_day.desk(desk_index).booker
            if desk_booker is not None:
                self._database.handle_event(
                    Event(
                        author=info.author_id,
                        time=datetime.now(),
                        event=UnbookDesk(start_date=booking_date, end_date=booking_date, desk_index=desk_index),
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
    def handle_error(self, info: CommandInfo, error: AppCommandError) -> Response:  # pragma: no cover
        match error:
            case discord.app_commands.errors.MissingAnyRole() | discord.app_commands.errors.MissingRole():
                return Response(message="You do not have permission to run this command.", ephemeral=True)
            case discord.app_commands.errors.CheckFailure():
                return Response(message="This command can only be used in the office channel.", ephemeral=True)
            case discord.app_commands.errors.CommandInvokeError() as error:
                match error.__cause__:
                    case EventError() as event_error:
                        return Response(message=event_error.message(info.format_user), ephemeral=True)
                    case dates.DateParseError(argument):
                        return Response(
                            f"Date {argument} could not be parsed. "
                            "Please use the format YYYY-MM-DD, 'today', 'tomorrow', or specify a weekday.",
                            ephemeral=True,
                        )
        raise error
