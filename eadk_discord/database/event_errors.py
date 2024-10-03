from collections.abc import Callable
from dataclasses import dataclass
from datetime import date as Date  # noqa: N812

from eadk_discord.database.event import Event


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
