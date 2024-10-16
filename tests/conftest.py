from collections.abc import Callable, Sequence
from datetime import date, datetime

import pytest

from eadk_discord.bot import CommandInfo, EADKBot
from eadk_discord.database.database import Database
from eadk_discord.database.event import Event, SetNumDesks

NOW: datetime = datetime.fromisoformat("2024-09-13")  # Friday
TODAY: date = NOW.date()

REGULAR_ROLE_ID: int = 1
ADMIN_ROLE_ID: int = 2


@pytest.fixture
def bot() -> EADKBot:
    database = Database.initialize(TODAY)
    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=TODAY, num_desks=6)))

    bot = EADKBot(database, set([REGULAR_ROLE_ID]), set([ADMIN_ROLE_ID]))

    return bot


def command_info(
    now: datetime = NOW,
    format_user: Callable[[int], str] = lambda user: str(user),
    author_id: int = 1,
    author_role_ids: Sequence[int] = [REGULAR_ROLE_ID, ADMIN_ROLE_ID],
) -> CommandInfo:
    return CommandInfo(
        now=now,
        format_user=format_user,
        author_id=author_id,
        author_role_ids=set(author_role_ids),
    )
