from datetime import timedelta

import pytest
from conftest import NOW, TODAY

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.bot_setup import INTERNAL_ERROR_MESSAGE
from eadk_discord.database.event_errors import NonExistentDeskError
from eadk_discord.database.state import DateTooEarlyError


def test_unbook(bot: EADKBot) -> None:
    database = bot.database

    database.state.day(TODAY)[0].desk(3).booker = 1

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    for i in range(0, 6):
        assert database.state.day(TODAY)[0].desk(i).booker is None


def test_unbook_with_desk(bot: EADKBot) -> None:
    state = bot.database.state

    state.day(TODAY)[0].desk(4).booker = 1

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=None,
        desk_num=5,
        end_date_str=None,
    )
    assert response.ephemeral is False
    for i in range(0, 6):
        assert state.day(TODAY)[0].desk(i).booker is None

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=None,
        desk_num=3,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE
    for i in range(0, 6):
        assert state.day(TODAY)[0].desk(i).booker is None


def test_unbook_with_user(bot: EADKBot) -> None:
    state = bot.database.state

    day = state.day(TODAY)[0]
    day.desk(3).booker = 5
    day.desk(1).booker = 4

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=5,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert day.desk(0).booker is None
    assert day.desk(1).booker == 4
    for i in range(2, 6):
        assert day.desk(i).booker is None


def test_unbook_with_user_desk(bot: EADKBot) -> None:
    state = bot.database.state

    day = state.day(TODAY)[0]
    day.desk(3).booker = 5
    day.desk(1).booker = 4

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=5,
        desk_num=4,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert day.desk(1).booker == 4
    assert day.desk(3).booker is None

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=None,
        user_id=5,
        desk_num=2,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE


def test_unbook_with_date(bot: EADKBot) -> None:
    state = bot.database.state

    date = TODAY + timedelta(3)

    today = state.day(TODAY)[0]
    day = state.day(date)[0]
    today.desk(3).booker = 1
    today.desk(4).booker = 4
    day.desk(0).booker = 3
    day.desk(4).booker = 1

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=date.isoformat(),
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is False
    assert today.desk(3).booker == 1
    assert today.desk(4).booker == 4
    assert day.desk(0).booker == 3
    for i in range(1, 6):
        assert day.desk(i).booker is None


def test_unbook_range_no_desk(bot: EADKBot) -> None:
    date = TODAY + timedelta(3)

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=None,
        end_date_str=date.isoformat(),
    )
    assert response.ephemeral


def test_unbook_range(bot: EADKBot) -> None:
    state = bot.database.state

    date = TODAY + timedelta(3)

    response = bot.makeowned(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        start_date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=1,
    )

    assert not response.ephemeral

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=1,
        end_date_str=date.isoformat(),
    )
    assert not response.ephemeral

    assert state.day(TODAY)[0].desk(0).owner == 1
    assert state.day(TODAY)[0].desk(0).booker is None
    assert state.day(TODAY + timedelta(1))[0].desk(0).owner == 1
    assert state.day(TODAY + timedelta(1))[0].desk(0).booker is None
    assert state.day(date)[0].desk(0).owner == 1
    assert state.day(date)[0].desk(0).booker is None


def test_unbook_range_unowned(bot: EADKBot) -> None:
    date = TODAY + timedelta(3)

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=1,
        end_date_str=date.isoformat(),
    )
    assert response.ephemeral


def test_unbook_in_past(bot: EADKBot) -> None:
    response = bot.unbook(
        CommandInfo(now=NOW + timedelta(2), format_user=lambda user: str(user), author_id=1),
        date_str=TODAY.isoformat(),
        user_id=None,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE


def test_unbook_too_early(bot: EADKBot) -> None:
    with pytest.raises(DateTooEarlyError):
        bot.unbook(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            date_str=(TODAY - timedelta(1)).isoformat(),
            user_id=0,
            desk_num=1,
            end_date_str=None,
        )


def test_unbook_non_existent_desk(bot: EADKBot) -> None:
    with pytest.raises(NonExistentDeskError):
        bot.unbook(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            date_str="today",
            user_id=0,
            desk_num=7,
            end_date_str=None,
        )
    with pytest.raises(NonExistentDeskError):
        bot.unbook(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            date_str="today",
            user_id=0,
            desk_num=0,
            end_date_str=None,
        )


def test_unbook_unbooked_desk(bot: EADKBot) -> None:
    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="today",
        user_id=0,
        desk_num=None,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE

    response = bot.unbook(
        CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
        date_str="today",
        user_id=0,
        desk_num=1,
        end_date_str=None,
    )
    assert response.ephemeral is True
    assert response.message != INTERNAL_ERROR_MESSAGE
