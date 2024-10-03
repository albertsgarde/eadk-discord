import pytest
from conftest import NOW

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.dates import DateParseError


def test_date_invalid(bot: EADKBot) -> None:
    with pytest.raises(DateParseError):
        bot.book(
            CommandInfo(now=NOW, format_user=lambda user: str(user), author_id=1),
            date_str="invalid",
            user_id=None,
            desk_num=None,
        )
