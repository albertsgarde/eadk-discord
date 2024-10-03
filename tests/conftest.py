from datetime import date, datetime

import pytest

from eadk_discord.bot import EADKBot
from eadk_discord.database.database import Database
from eadk_discord.database.event import Event, SetNumDesks

NOW: datetime = datetime.fromisoformat("2024-09-13")  # Friday
TODAY: date = NOW.date()


@pytest.fixture
def bot() -> EADKBot:
    database = Database.initialize(TODAY)
    database.handle_event(Event(author=None, time=NOW, event=SetNumDesks(date=TODAY, num_desks=6)))

    bot = EADKBot(database)

    return bot
