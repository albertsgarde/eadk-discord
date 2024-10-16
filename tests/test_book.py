from datetime import timedelta
from itertools import chain

import pytest
from conftest import NOW, TODAY, command_info

from eadk_discord.bot import EADKBot
from eadk_discord.bot_setup import INTERNAL_ERROR_MESSAGE
from eadk_discord.database.event_errors import DeskAlreadyBookedError, NonExistentDeskError
from eadk_discord.database.state import DateTooEarlyError


def test_book(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        command_info(),
        date_str=None,
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker == 1
    for i in range(1, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_desk(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        command_info(),
        date_str=None,
        user_id=None,
        desk_num=5,
        end_date_str=None,
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
        command_info(),
        date_str=None,
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker == 0
    assert database.state.day(TODAY)[0].desk(1).booker == 1
    for i in range(2, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_user(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        command_info(),
        date_str=None,
        user_id=7,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker == 7
    for i in range(1, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_user_desk(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        command_info(),
        date_str=None,
        user_id=4,
        desk_num=5,
        end_date_str=None,
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
        command_info(),
        date_str="tomorrow",
        user_id=None,
        desk_num=None,
        end_date_str=None,
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
        command_info(),
        date_str="tomorrow",
        user_id=None,
        desk_num=3,
        end_date_str=None,
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
        command_info(),
        date_str="tomorrow",
        user_id=8,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert database.state.day(tomorrow)[0].desk(0).booker == 8
    for i in range(1, 6):
        assert database.state.day(tomorrow)[0].desk(i).booker is None
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_range_no_desk(bot: EADKBot) -> None:
    response = bot.book(
        command_info(),
        date_str="today",
        user_id=None,
        desk_num=None,
        end_date_str="tomorrow",
    )
    assert response.ephemeral is True


def test_book_range_with_desk(bot: EADKBot) -> None:
    database = bot.database

    tomorrow = TODAY + timedelta(1)

    response = bot.makeowned(
        command_info(),
        start_date_str="today",
        user_id=None,
        desk_num=3,
    )

    assert not response.ephemeral

    response = bot.unbook(
        command_info(),
        date_str="today",
        user_id=None,
        desk_num=3,
        end_date_str=(TODAY + timedelta(5)).isoformat(),
    )

    assert not response.ephemeral

    response = bot.book(
        command_info(),
        date_str="today",
        user_id=None,
        desk_num=3,
        end_date_str="tomorrow",
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(2).booker == 1
    assert database.state.day(tomorrow)[0].desk(2).booker == 1
    for i in chain(range(0, 2), range(3, 6)):
        assert database.state.day(TODAY)[0].desk(i).booker is None
        assert database.state.day(tomorrow)[0].desk(i).booker is None
    for i in range(0, 6):
        assert database.state.day(tomorrow + timedelta(1))[0].desk(i).booker is None


def test_book_range_unowned(bot: EADKBot) -> None:
    response = bot.book(
        command_info(),
        date_str="today",
        user_id=None,
        desk_num=3,
        end_date_str="tomorrow",
    )
    assert response.ephemeral


def test_book_weekday_same_week(bot: EADKBot) -> None:
    database = bot.database

    sunday = TODAY + timedelta(2)

    response = bot.book(
        command_info(),
        date_str="sunday",
        user_id=None,
        desk_num=None,
        end_date_str=None,
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
        command_info(),
        date_str="tuesday",
        user_id=None,
        desk_num=None,
        end_date_str=None,
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
        command_info(),
        date_str=date.isoformat(),
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert database.state.day(date)[0].desk(0).booker == 1
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_book_with_date_user_desk(bot: EADKBot) -> None:
    database = bot.database

    response = bot.book(
        command_info(),
        date_str="today",
        user_id=3,
        desk_num=2,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert database.state.day(TODAY)[0].desk(0).booker is None
    assert database.state.day(TODAY)[0].desk(1).booker == 3


def test_book_in_past(bot: EADKBot) -> None:
    response = bot.book(
        command_info(now=NOW + timedelta(2), format_user=lambda user: str(user), author_id=1),
        date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE


def test_book_fully_booked(bot: EADKBot) -> None:
    database = bot.database

    for i in range(6):
        database.state.day(TODAY)[0].desk(i).booker = i

    response = bot.book(
        command_info(now=NOW, format_user=lambda user: str(user), author_id=7),
        date_str=None,
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE


def test_book_too_early(bot: EADKBot) -> None:
    with pytest.raises(DateTooEarlyError):
        bot.book(
            command_info(),
            date_str=(TODAY - timedelta(1)).isoformat(),
            user_id=0,
            desk_num=1,
            end_date_str=None,
        )


def test_book_non_existent_desk(bot: EADKBot) -> None:
    with pytest.raises(NonExistentDeskError):
        bot.book(
            command_info(),
            date_str="today",
            user_id=0,
            desk_num=7,
            end_date_str=None,
        )
    with pytest.raises(NonExistentDeskError):
        bot.book(
            command_info(),
            date_str="today",
            user_id=0,
            desk_num=0,
            end_date_str=None,
        )


def test_book_already_booked(bot: EADKBot) -> None:
    database = bot.database

    database.state.day(TODAY)[0].desk(0).booker = 0

    with pytest.raises(DeskAlreadyBookedError):
        bot.book(
            command_info(),
            date_str="today",
            user_id=None,
            desk_num=1,
            end_date_str=None,
        )
