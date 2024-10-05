from datetime import timedelta
from itertools import chain

import pytest
from conftest import NOW, TODAY

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database.event import Event, SetNumDesks
from eadk_discord.database.event_errors import DeskAlreadyOwnedError, NonExistentDeskError


def test_makeowned(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)
    distant_date = TODAY + timedelta(days=23)

    response = bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=tomorrow.isoformat(),
        user_id=None,
        desk_num=3,
    )
    assert response.ephemeral is False
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None
        assert database.state.day(TODAY)[0].desk(i).owner is None
    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
        assert database.state.day(tomorrow)[0].desk(i).owner is None
    assert database.state.day(tomorrow)[0].desk(2).booker == 1
    assert database.state.day(tomorrow)[0].desk(2).owner == 1

    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(distant_date)[0].desk(i).booker is None
        assert database.state.day(distant_date)[0].desk(i).owner is None
    assert database.state.day(distant_date)[0].desk(2).booker == 1
    assert database.state.day(distant_date)[0].desk(2).owner == 1


def test_makeowned_with_user(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)
    distant_date = TODAY + timedelta(days=23)

    response = bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=tomorrow.isoformat(),
        user_id=4,
        desk_num=3,
    )
    assert response.ephemeral is False
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None
        assert database.state.day(TODAY)[0].desk(i).owner is None
    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
        assert database.state.day(tomorrow)[0].desk(i).owner is None
    assert database.state.day(tomorrow)[0].desk(2).booker == 4
    assert database.state.day(tomorrow)[0].desk(2).owner == 4

    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(distant_date)[0].desk(i).booker is None
        assert database.state.day(distant_date)[0].desk(i).owner is None
    assert database.state.day(distant_date)[0].desk(2).booker == 4
    assert database.state.day(distant_date)[0].desk(2).owner == 4


def test_makeowned_booked(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)
    distant_date = TODAY + timedelta(days=23)

    database.state.day(distant_date)[0].desk(2).booker = 4

    response = bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=tomorrow.isoformat(),
        user_id=None,
        desk_num=3,
    )
    assert response.ephemeral is False
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None
        assert database.state.day(TODAY)[0].desk(i).owner is None
    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
        assert database.state.day(tomorrow)[0].desk(i).owner is None
    assert database.state.day(tomorrow)[0].desk(2).booker == 1
    assert database.state.day(tomorrow)[0].desk(2).owner == 1

    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(distant_date)[0].desk(i).booker is None
        assert database.state.day(distant_date)[0].desk(i).owner is None
    assert database.state.day(distant_date)[0].desk(2).booker == 4
    assert database.state.day(distant_date)[0].desk(2).owner == 1


def test_makeowned_varying_desk_num(bot: EADKBot) -> None:
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

    assert database.state.day(date1 - timedelta(days=1))[0].desk(4).owner == 1
    assert database.state.day(date2)[0].desk(4).owner is None


def test_makeowned_non_existent_desk(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)

    with pytest.raises(NonExistentDeskError):
        bot.makeowned(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            start_date_str=tomorrow.isoformat(),
            user_id=None,
            desk_num=7,
        )

    with pytest.raises(NonExistentDeskError):
        bot.makeowned(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            start_date_str=tomorrow.isoformat(),
            user_id=None,
            desk_num=0,
        )

    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None
        assert database.state.day(TODAY)[0].desk(i).owner is None
    for i in range(0, 6):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
        assert database.state.day(tomorrow)[0].desk(i).owner is None


def test_makeowned_owned_desk(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(days=1)
    distant_date = TODAY + timedelta(days=23)

    database.state.day(distant_date)[0].desk(2).owner = 4

    with pytest.raises(DeskAlreadyOwnedError):
        bot.makeowned(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            start_date_str=tomorrow.isoformat(),
            user_id=None,
            desk_num=3,
        )
