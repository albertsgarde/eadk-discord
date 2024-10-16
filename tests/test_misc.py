from datetime import timedelta

import pytest
from conftest import NOW, TODAY, command_info

from eadk_discord.bot import EADKBot
from eadk_discord.database.event import Event, SetNumDesks
from eadk_discord.database.event_errors import DateTooEarlyError, NonExistentDeskError, RemoveDeskError
from eadk_discord.dates import DateParseError


def test_date_invalid(bot: EADKBot) -> None:
    with pytest.raises(DateParseError):
        bot.book(
            command_info(),
            date_str="invalid",
            user_id=None,
            desk_num=None,
            end_date_str=None,
        )


def test_info(bot: EADKBot) -> None:
    response = bot.info(command_info(), date_str=None)
    assert response.ephemeral is True

    with pytest.raises(DateTooEarlyError):
        response = bot.info(command_info(), date_str="2021-01-01")


def test_change_desk_num(bot: EADKBot) -> None:
    database = bot.database

    date1 = TODAY + timedelta(days=7)
    date2 = TODAY + timedelta(days=42)

    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=date1, num_desks=7)))

    database.state.day(date1)[0].desk(6)
    database.state.day(date2)[0].desk(6)
    with pytest.raises(NonExistentDeskError):
        database.state.day(date1)[0].desk(7)

    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=date2, num_desks=3)))

    database.state.day(date1)[0].desk(6)
    with pytest.raises(NonExistentDeskError):
        database.state.day(date2)[0].desk(6)
    with pytest.raises(NonExistentDeskError):
        database.state.day(date2)[0].desk(3)
    with pytest.raises(NonExistentDeskError):
        database.state.day(date2 + timedelta(1))[0].desk(3)
    database.state.day(date2)[0].desk(2)


def test_change_desk_num_owned_or_used(bot: EADKBot) -> None:
    database = bot.database

    date1 = TODAY + timedelta(days=7)
    date2 = TODAY + timedelta(days=42)

    bot.book(
        command_info(),
        date_str=date1.isoformat(),
        user_id=None,
        desk_num=6,
        end_date_str=None,
    )

    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=date1, num_desks=7)))

    bot.book(
        command_info(),
        date_str=date2.isoformat(),
        user_id=None,
        desk_num=7,
        end_date_str=None,
    )

    with pytest.raises(RemoveDeskError) as e:
        database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=date1, num_desks=6)))
    assert e.value.desk_index == 6
