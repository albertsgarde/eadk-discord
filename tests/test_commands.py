from datetime import date, datetime, timedelta

import pytest

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database import Database
from eadk_discord.database.event import Event, SetNumDesks
from eadk_discord.database.state import DateTooEarlyError

NOW: datetime = datetime.fromisoformat("2024-09-14")  # Saturday
TODAY: date = NOW.date()


@pytest.fixture
def bot() -> EADKBot:
    database = Database.initialize(TODAY)
    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=TODAY, num_desks=6)))

    bot = EADKBot(database)

    return bot


def test_book(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), "today", user_id=3, desk_arg=2
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker is None
    assert database.state.day(TODAY)[0].desk(1).booker == 3


def test_book_too_early(bot: EADKBot) -> None:
    with pytest.raises(DateTooEarlyError):
        bot.book(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            (TODAY - timedelta(1)).isoformat(),
            user_id=0,
            desk_arg=1,
        )
