from datetime import datetime, timedelta

import pytest

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database import Database
from eadk_discord.event import Event, SetNumDesks
from eadk_discord.state import DateTooEarlyError


def test() -> None:
    now = datetime.fromisoformat("2024-09-14")  # Saturday
    today = now.date()

    database = Database.initialize(now)
    database.handle_event(Event(author=None, time=now, event=SetNumDesks(date=today, num_desks=6)))

    bot = EADKBot(database)

    with pytest.raises(DateTooEarlyError):
        bot.book(
            CommandInfo(now=now, format_user=lambda user: str(user), author_id=1),
            (today - timedelta(1)).isoformat(),
            user_id=0,
            desk_arg=1,
        )

    response = bot.book(
        CommandInfo(now=now, format_user=lambda user: str(user), author_id=1), today.isoformat(), user_id=3, desk_arg=2
    )
    assert response.ephemeral is False
    assert database.state.day(today)[0].desk(0).booker is None
    assert database.state.day(today)[0].desk(1).booker == 3
