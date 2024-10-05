import pytest
from conftest import NOW

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database.event_errors import DateTooEarlyError
from eadk_discord.dates import DateParseError


def test_date_invalid(bot: EADKBot) -> None:
    with pytest.raises(DateParseError):
        bot.book(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            date_str="invalid",
            user_id=None,
            desk_num=None,
        )


def test_info(bot: EADKBot) -> None:
    response = bot.info(CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), date_str=None)
    assert response.ephemeral is True

    with pytest.raises(DateTooEarlyError):
        response = bot.info(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1), date_str="2021-01-01"
        )
