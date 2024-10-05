from dataclasses import dataclass
from datetime import date, datetime, timedelta

from beartype import beartype

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@dataclass
class DateParseError(Exception):
    argument: str


@beartype
def parse_date_arg(argument: str, today: date) -> date:
    if argument.lower() == "today":
        return today
    elif argument.lower() == "tomorrow":
        return today + timedelta(days=1)
    elif argument.lower() in WEEKDAYS:
        weekday = WEEKDAYS.index(argument.lower())
        return today + timedelta(days=(weekday - today.weekday()) % 7)
    # Try to parse the argument as an integer representing the day of the month
    else:
        try:
            return date.fromisoformat(argument)
        except Exception:
            raise DateParseError(argument) from Exception


@beartype
def get_booking_date(booking_date_arg: str | None, now: datetime) -> date:
    """
    Returns a tuple of two values:
    - A boolean indicating whether it is currently before 17:00.
    - A date object representing the date on which desks should be booked.
    """
    if booking_date_arg is not None:
        return parse_date_arg(booking_date_arg, now.date())
    booking_date = now.date() if now.hour < 17 else now.date() + timedelta(days=1)
    return booking_date
