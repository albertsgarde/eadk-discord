import itertools
from datetime import date as Date  # noqa: N812
from datetime import timedelta as TimeDelta  # noqa: N812

from beartype import beartype
from beartype.typing import Sequence  # noqa: N812
from pydantic import BaseModel, Field

from eadk_discord.database.event_errors import (
    DateTooEarlyError,
    DeskAlreadyBookedError,
    DeskAlreadyOwnedError,
    DeskNotBookedError,
    DeskNotOwnedError,
    NonExistentDeskError,
    RemoveDeskError,
)

from .event import BookDesk, Event, MakeFlex, MakeOwned, SetNumDesks, UnbookDesk
from .history import History


class DeskStatus(BaseModel):
    booker: int | None = Field(serialization_alias="booker")
    owner: int | None = Field(serialization_alias="owner")

    @beartype
    def _book(self, user: int) -> bool:
        """
        Returns True if the desk was successfully booked, False if the desk was already booked.
        """
        if self.booker:
            return False
        else:
            self.booker = user
            return True

    @beartype
    def _unbook(self) -> bool:
        """
        Returns True if the desk was successfully unbooked, False if the desk was not booked.
        """
        if self.booker:
            self.booker = None
            return True
        else:
            return False

    @beartype
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

    @beartype
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

    @beartype
    @classmethod
    def create_unbooked(cls, date: Date, num_desks: int) -> "Day":
        return cls(date=date, desks=[DeskStatus(booker=None, owner=None) for _ in range(num_desks)])

    @beartype
    @classmethod
    def create_from_previous(cls, previous: "Day") -> "Day":
        return cls(
            date=previous.date + TimeDelta(1),
            desks=[DeskStatus(booker=desk.owner, owner=desk.owner) for desk in previous.desks],
        )

    @beartype
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

    @beartype
    def get_available_desk(self) -> int | None:
        """
        Returns the first available desk, or None if all desks are booked.
        """
        for i, desk in enumerate(self.desks):
            if desk.booker is None:
                return i
        return None

    @beartype
    def available_desks(self) -> list[int]:
        """
        Returns a list of indices of available desks.
        """
        return [i for i, desk in enumerate(self.desks) if desk.booker is None]

    @beartype
    def booked_desks(self, member: int) -> list[int]:
        """
        Returns the index of the desk booked by the given member, or None if the member has not booked a desk.
        """
        return [i for i, desk in enumerate(self.desks) if desk.booker == member]


class State(BaseModel):
    start_date: Date = Field(serialization_alias="start_date")
    days: list[Day] = Field(serialization_alias="days")

    @beartype
    @staticmethod
    def initialize(history: History) -> "State":
        state = State(start_date=history.start_date, days=[Day.create_unbooked(history.start_date, 0)])
        for event in history.history:
            state.handle_event(event)
        return state

    @beartype
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

    @beartype
    def handle_event(self, event: Event) -> None:
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

    @beartype
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

    @beartype
    def _book_desk(self, event: BookDesk) -> None:
        day, _ = self.day(event.date)
        desk_index = event.desk_index
        if desk_index >= len(day.desks) or desk_index < 0:
            raise NonExistentDeskError(desk=desk_index, num_desks=len(day.desks), day=event.date)
        desk = day.desks[desk_index]
        if desk.booker is not None:
            raise DeskAlreadyBookedError(booker=desk.booker, desk=desk_index, day=event.date)
        desk.booker = event.user

    @beartype
    def _unbook_desk(self, event: UnbookDesk) -> None:
        day, _ = self.day(event.date)
        desk_index = event.desk_index
        if desk_index >= len(day.desks):
            raise NonExistentDeskError(desk=desk_index, num_desks=len(day.desks), day=event.date)
        desk = day.desks[desk_index]
        if not desk.booker:
            raise DeskNotBookedError(desk=desk_index, day=event.date)
        desk.booker = None

    @beartype
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

    @beartype
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
