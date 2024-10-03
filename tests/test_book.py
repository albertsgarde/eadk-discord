from datetime import timedelta
from itertools import chain

import pytest
from conftest import NOW, TODAY

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database.event_errors import DeskAlreadyBookedError, NonExistentDeskError
from eadk_discord.database.state import DateTooEarlyError


def test_book(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=None,
        desk_num=None,
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker == 1
    for i in range(1, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_desk(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), date_str=None, user_id=None, desk_num=5
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(4).booker == 1
    for i in range(0, 4):
        assert database.state.day(TODAY)[0].desk(i).booker is None
    assert database.state.day(TODAY)[0].desk(5).booker is None


def test_book2(bot: EADKBot) -> None:
    database = bot.database

    database.state.day(TODAY)[0].desk(0).booker = 0

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=None,
        desk_num=None,
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker == 0
    assert database.state.day(TODAY)[0].desk(1).booker == 1
    for i in range(2, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_user(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), date_str=None, user_id=7, desk_num=None
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker == 7
    for i in range(1, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_user_desk(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), date_str=None, user_id=4, desk_num=5
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(4).booker == 4
    for i in range(0, 4):
        assert database.state.day(TODAY)[0].desk(i).booker is None
    assert database.state.day(TODAY)[0].desk(5).booker is None


def test_book_with_date(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(1)

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="tomorrow",
        user_id=None,
        desk_num=None,
    )
    assert response.ephemeral is False
    assert database.state.day(tomorrow)[0].desk(0).booker == 1
    for i in range(1, 6):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_date_desk(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(1)

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="tomorrow",
        user_id=None,
        desk_num=3,
    )
    assert response.ephemeral is False
    assert database.state.day(tomorrow)[0].desk(2).booker == 1
    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_date_user(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(1)

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="tomorrow",
        user_id=8,
        desk_num=None,
    )
    assert response.ephemeral is False
    assert database.state.day(tomorrow)[0].desk(0).booker == 8
    for i in range(1, 6):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_weekday_same_week(bot: EADKBot) -> None:
    database = bot.database

    sunday = TODAY + timedelta(2)

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="sunday",
        user_id=None,
        desk_num=None,
    )

    assert response.ephemeral is False
    assert database.state.day(sunday)[0].desk(0).booker == 1
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None
    for i in range(1, 6):
        assert database.state.day(sunday)[0].desk(i).booker is None


def test_book_weekday_next_week(bot: EADKBot) -> None:
    database = bot.database

    tuesday = TODAY + timedelta(4)

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="tuesday",
        user_id=None,
        desk_num=None,
    )

    assert response.ephemeral is False
    assert database.state.day(tuesday)[0].desk(0).booker == 1
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None
    for i in range(1, 6):
        assert database.state.day(tuesday)[0].desk(i).booker is None


def test_book_date(bot: EADKBot) -> None:
    database = bot.database

    date = TODAY + timedelta(23)

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=date.isoformat(),
        user_id=None,
        desk_num=None,
    )
    assert response.ephemeral is False
    assert database.state.day(date)[0].desk(0).booker == 1
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_date_user_desk(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), date_str="today", user_id=3, desk_num=2
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
            desk_num=1,
        )


def test_book_non_existant_desk(bot: EADKBot) -> None:
    with pytest.raises(NonExistentDeskError):
        bot.book(CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), "today", user_id=0, desk_num=7)
    with pytest.raises(NonExistentDeskError):
        bot.book(CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), "today", user_id=0, desk_num=0)


def test_book_already_booked(bot: EADKBot) -> None:
    database = bot.database

    database.state.day(TODAY)[0].desk(0).booker = 0

    with pytest.raises(DeskAlreadyBookedError):
        bot.book(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), "today", user_id=None, desk_num=1
        )
