from datetime import date, timedelta

from discord import Interaction
from discord.app_commands import Transformer

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def parse_date_arg(argument: str, today: date) -> date | str:
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
            return "Could not parse date argument.\nPlease format the date as YYYY-MM-DD"


class DateConverter(Transformer):
    async def transform(self, interaction: Interaction, argument: str) -> date | str:
        today = date.today()
        return parse_date_arg(argument, today)
