from datetime import timedelta

import pytest
from conftest import NOW, TODAY

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database.event import Event, SetNumDesks
from eadk_discord.database.event_errors import DeskNotOwnedError, NonExistentDeskError


def test_makeflex(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)
    distant_date = TODAY + timedelta(days=23)
    distant_date2 = TODAY + timedelta(days=43)

    bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=tomorrow.isoformat(),
        user_id=None,
        desk_num=3,
    )

    assert database.state.day(distant_date)[0].desk(2).booker == 1
    assert database.state.day(distant_date)[0].desk(2).owner == 1
    assert database.state.day(distant_date2)[0].desk(2).booker == 1
    assert database.state.day(distant_date2)[0].desk(2).owner == 1

    response = bot.makeflex(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=distant_date.isoformat(),
        desk_num=3,
    )
    assert response.ephemeral is False
    assert database.state.day(distant_date - timedelta(days=1))[0].desk(2).booker == 1
    assert database.state.day(distant_date - timedelta(days=1))[0].desk(2).owner == 1
    assert database.state.day(distant_date)[0].desk(2).booker is None
    assert database.state.day(distant_date)[0].desk(2).owner is None
    assert database.state.day(distant_date2)[0].desk(2).booker is None
    assert database.state.day(distant_date2)[0].desk(2).owner is None


def test_makeflex_booked(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)
    distant_date = TODAY + timedelta(days=23)
    distant_date2 = TODAY + timedelta(days=43)

    database.state.day(distant_date2)[0].desk(2).booker = 4

    bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=tomorrow.isoformat(),
        user_id=None,
        desk_num=3,
    )

    assert database.state.day(distant_date)[0].desk(2).booker == 1
    assert database.state.day(distant_date)[0].desk(2).owner == 1
    assert database.state.day(distant_date2)[0].desk(2).booker == 4
    assert database.state.day(distant_date2)[0].desk(2).owner == 1

    response = bot.makeflex(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=distant_date.isoformat(),
        desk_num=3,
    )
    assert response.ephemeral is False
    assert database.state.day(distant_date - timedelta(days=1))[0].desk(2).booker == 1
    assert database.state.day(distant_date - timedelta(days=1))[0].desk(2).owner == 1
    assert database.state.day(distant_date)[0].desk(2).booker is None
    assert database.state.day(distant_date)[0].desk(2).owner is None
    assert database.state.day(distant_date2)[0].desk(2).booker == 4
    assert database.state.day(distant_date2)[0].desk(2).owner is None


def test_makeflex_varying_desk_num(bot: EADKBot) -> None:
    database = bot.database

    date1 = TODAY + timedelta(days=3)
    date2 = TODAY + timedelta(days=7)

    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=date1, num_desks=4)))
    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=date2, num_desks=6)))

    bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=5,
    )

    bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=date2.isoformat(),
        user_id=None,
        desk_num=5,
    )

    bot.makeflex(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=(TODAY + timedelta(1)).isoformat(),
        desk_num=5,
    )

    assert database.state.day(TODAY)[0].desk(4).owner == 1
    assert database.state.day(TODAY + timedelta(1))[0].desk(4).owner is None
    assert database.state.day(date1 - timedelta(days=1))[0].desk(4).owner is None
    assert database.state.day(date2)[0].desk(4).owner == 1


def test_makeflex_non_existent_desk(bot: EADKBot) -> None:
    with pytest.raises(NonExistentDeskError):
        bot.makeflex(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            start_date_str=TODAY.isoformat(),
            desk_num=7,
        )
    with pytest.raises(NonExistentDeskError):
        bot.makeflex(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            start_date_str=TODAY.isoformat(),
            desk_num=0,
        )


def test_makeflex_flex_desk(bot: EADKBot) -> None:
    with pytest.raises(DeskNotOwnedError):
        bot.makeflex(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            start_date_str=TODAY.isoformat(),
            desk_num=1,
        )
