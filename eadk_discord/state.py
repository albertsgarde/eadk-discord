import itertools
from dataclasses import dataclass
from datetime import date as Date  # noqa: N812
from datetime import timedelta as TimeDelta  # noqa: N812

from beartype.typing import Callable, Sequence  # noqa: N812
from pydantic import BaseModel, Field

from .event import BookDesk, Event, MakeFlex, MakeOwned, SetNumDesks, UnbookDesk
from .history import History

MAX_FUTURE_DAYS: int = 366


class DeskStatus(BaseModel):
    booker: int | None = Field(serialization_alias="booker")
    owner: int | None = Field(serialization_alias="owner")

    def _book(self, user: int) -> bool:
        """
        Returns True if the desk was successfully booked, False if the desk was already booked.
        """
        if self.booker:
            return False
        else:
            self.booker = user
            return True

    def _unbook(self) -> bool:
        """
        Returns True if the desk was successfully unbooked, False if the desk was not booked.
        """
        if self.booker:
            self.booker = None
            return True
        else:
            return False

    def _make_owned(self, user: int) -> bool:
        """
        Returns True if the desk was successfully permanently booked, False if the desk was already permanently booked.
        """
        if self.owner:
            return False
        else:
            if self.booker is None:
                self.booker = user
            self.owner = user
            return True

    def _make_flex(self) -> bool:
        """
        Returns True if the desk was successfully unpermanently booked, False if the desk was not permanently booked.
        """
        if self.owner:
            if self.owner == self.booker:
                self.booker = None
            self.owner = None
            return True
        else:
            return False


class Day(BaseModel):
    date: Date = Field()
    desks: Sequence[DeskStatus] = Field()

    @classmethod
    def create_unbooked(cls, date: Date, num_desks: int) -> "Day":
        return cls(date=date, desks=[DeskStatus(booker=None, owner=None) for _ in range(num_desks)])

    @classmethod
    def create_from_previous(cls, previous: "Day") -> "Day":
        return cls(
            date=previous.date + TimeDelta(1),
            desks=[DeskStatus(booker=desk.owner, owner=desk.owner) for desk in previous.desks],
        )

    def desk(self, desk: int) -> DeskStatus:
        """
        Returns the DeskStatus object for the given desk.
        """
        if desk < 0:
            raise ValueError("desk number must be non-negative")
        elif desk >= len(self.desks):
            raise ValueError("desk number is out of range. There are only {len(self.desks)} desks.")
        result: DeskStatus = self.desks[desk]
        return result

    def get_available_desk(self) -> int | None:
        """
        Returns the first available desk, or None if all desks are booked.
        """
        for i, desk in enumerate(self.desks):
            if desk.booker is None:
                return i
        return None

    def available_desks(self) -> list[int]:
        """
        Returns a list of indices of available desks.
        """
        return [i for i, desk in enumerate(self.desks) if desk.booker is None]

    def booked_desks(self, member: int) -> list[int]:
        """
        Returns the index of the desk booked by the given member, or None if the member has not booked a desk.
        """
        return [i for i, desk in enumerate(self.desks) if desk.booker == member]


class EventError(Exception):
    def message(self, format_user: Callable[[int], str]) -> str:
        raise NotImplementedError()


@dataclass
class HandleEventError(Exception):
    event: Event
    error: EventError

    def message(self, format_user: Callable[[int], str]) -> str:
        return self.error.message(format_user)


@dataclass
class DateTooEarlyError(EventError):
    """
    Raised when trying to access a date before the start date.
    """

    date: Date
    start_date: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        return f"Date {self.date} is before the start date {self.start_date}."


@dataclass
class RemoveDeskError(EventError):
    """
    Raised when a desk cannot be removed because it is still booked.
    """

    booker: int | None
    owner: int | None
    desk_index: int
    day: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        if self.booker and self.owner is None:
            return (
                f"Desk {self.desk_index + 1} on {self.day} cannot be removed "
                f"because it is booked by {format_user(self.booker)}"
            )
        elif (self.booker is None and self.owner) or self.booker and self.booker == self.owner:
            return (
                f"Desk {self.desk_index + 1} on {self.day} cannot be removed "
                f"because it is owned by {format_user(self.owner)}"
            )
        elif self.booker and self.owner:
            return (
                f"Desk {self.desk_index + 1} on {self.day} cannot be removed "
                f"because it is booked by {format_user(self.booker)} and owned by {format_user(self.owner)}."
            )
        else:
            raise ValueError("booker and owner cannot both be None")


@dataclass
class NonExistentDeskError(EventError):
    """
    Raised when trying to book a desk that does not exist.
    """

    desk: int
    num_desks: int
    day: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        return f"Desk {self.desk + 1} on {self.day} does not exist. On that day there are only {self.num_desks} desks."


@dataclass
class DeskAlreadyBookedError(EventError):
    """
    Raised when trying to book a desk that is already booked.
    """

    booker: int
    desk: int
    day: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        return f"Desk {self.desk + 1} on {self.day} is already booked by {format_user(self.booker)}."


@dataclass
class DeskNotBookedError(EventError):
    """
    Raised when trying to unbook a desk that is not booked.
    """

    desk: int
    day: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        return f"Desk {self.desk + 1} on {self.day} is not booked."


@dataclass
class DeskAlreadyOwnedError(EventError):
    """
    Raised when trying to permanently book a desk that is already permanently booked.
    """

    owner: int
    desk: int
    day: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        return f"Desk {self.desk + 1} on {self.day} is already owned by {format_user(self.owner)}."


@dataclass
class DeskNotOwnedError(EventError):
    """
    Raised when trying to make an unowned desk flex.
    """

    desk: int
    day: Date

    def message(self, format_user: Callable[[int], str]) -> str:
        return f"Desk {self.desk + 1} on {self.day} is already a flex desk."


class State(BaseModel):
    start_date: Date = Field(serialization_alias="start_date")
    days: list[Day] = Field(serialization_alias="days")

    @staticmethod
    def initialize(history: History) -> "State":
        state = State(start_date=history.start_date, days=[Day.create_unbooked(history.start_date, 0)])
        for event in history.history:
            state.handle_event(event)
        return state

    def day(self, date: Date) -> tuple[Day, int]:
        """
        Returns the Day object for the given date, or None if the date is not in the database.
        """
        day_index = (date - self.start_date).days
        if day_index < 0:
            raise DateTooEarlyError(date=date, start_date=self.start_date)
        while len(self.days) <= day_index:
            self.days.append(Day.create_from_previous(self.days[-1]))
        return self.days[day_index], day_index

    def handle_event(self, event: Event) -> None:
        try:
            match event.event:
                case SetNumDesks():
                    self._set_num_desks(event.event)
                case BookDesk():
                    self._book_desk(event.event)
                case UnbookDesk():
                    self._unbook_desk(event.event)
                case MakeOwned():
                    self._make_owned(event.event)
                case MakeFlex():
                    self._make_flex(event.event)
        except EventError as e:
            raise HandleEventError(event=event, error=e) from e

    def _set_num_desks(self, event: SetNumDesks) -> None:
        _, day_index = self.day(event.date)
        for day in self.days[day_index:]:
            if len(day.desks) > event.num_desks:
                for desk_index, desk in enumerate(day.desks[event.num_desks :]):
                    desk_index += event.num_desks
                    if desk.booker or desk.owner:
                        raise RemoveDeskError(booker=desk.booker, owner=desk.owner, desk_index=desk_index, day=day.date)
            else:
                day.desks = list(
                    itertools.chain(
                        day.desks,
                        (DeskStatus(booker=None, owner=None) for _ in range(event.num_desks - len(day.desks))),
                    )
                )
        for day in self.days[day_index:]:
            day.desks = day.desks[: event.num_desks]

    def _book_desk(self, event: BookDesk) -> None:
        day, _ = self.day(event.date)
        desk_index = event.desk_index
        if desk_index >= len(day.desks):
            raise NonExistentDeskError(desk=desk_index, num_desks=len(day.desks), day=event.date)
        desk = day.desks[desk_index]
        if desk.booker:
            raise DeskAlreadyBookedError(booker=desk.booker, desk=desk_index, day=event.date)
        desk.booker = event.user

    def _unbook_desk(self, event: UnbookDesk) -> None:
        day, _ = self.day(event.date)
        desk_index = event.desk_index
        if desk_index >= len(day.desks):
            raise NonExistentDeskError(desk=desk_index, num_desks=len(day.desks), day=event.date)
        desk = day.desks[desk_index]
        if not desk.booker:
            raise DeskNotBookedError(desk=desk_index, day=event.date)
        desk.booker = None

    def _make_owned(self, event: MakeOwned) -> None:
        day, day_index = self.day(event.start_date)
        desk_index = event.desk_index
        if desk_index >= len(day.desks):
            raise NonExistentDeskError(desk=desk_index, num_desks=len(day.desks), day=event.start_date)
        for day in self.days[day_index:]:
            if desk_index >= len(day.desks):
                break
            owner = day.desks[desk_index].owner
            if owner and owner != event.user:
                raise DeskAlreadyOwnedError(owner=owner, desk=desk_index, day=day.date)
        for day in self.days[day_index:]:
            if desk_index >= len(day.desks):
                break
            day.desks[desk_index]._make_owned(event.user)

    def _make_flex(self, event: MakeFlex) -> None:
        day, day_index = self.day(event.start_date)
        desk_index = event.desk_index
        if desk_index >= len(day.desks):
            raise NonExistentDeskError(desk=desk_index, num_desks=len(day.desks), day=event.start_date)
        if day.desks[desk_index].owner is None:
            raise DeskNotOwnedError(desk=desk_index, day=event.start_date)
        else:
            desk_owner = day.desks[desk_index].owner
        for day in self.days[day_index:]:
            if desk_index >= len(day.desks) or day.desks[desk_index].owner != desk_owner:
                break
            desk = day.desks[desk_index]
            desk._make_flex()
