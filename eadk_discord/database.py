from datetime import date as Date  # noqa: N812
from pathlib import Path

from beartype import beartype
from pydantic import BaseModel, Field

from eadk_discord.history import History

from .event import Event
from .state import State


class Database(BaseModel):
    history: History = Field()
    state: State = Field()

    @beartype
    @staticmethod
    def initialize(start_date: Date) -> "Database":
        history = History.initialize(start_date)
        state = State.initialize(history)
        return Database(history=history, state=state)

    @beartype
    def save(self, path: Path) -> None:
        with path.open("w") as file:
            file.write(self.history.to_json())

    @beartype
    @staticmethod
    def load(path: Path) -> "Database":
        with path.open("r") as file:
            data = file.read()
        history = History.from_json(data)
        state = State.initialize(history)
        return Database(history=history, state=state)

    @beartype
    def handle_event(self, event: Event) -> None:
        self.state.handle_event(event)
        self.history.append(event)
