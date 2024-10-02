from datetime import date as Date  # noqa: N812

from beartype.typing import Any  # noqa: N812
from pydantic import BaseModel, Field

from .event import Event


class History(BaseModel):
    start_date: Date = Field()
    history: list[Event] = Field()

    @staticmethod
    def initialize(start_date: Date) -> "History":
        return History(start_date=start_date, history=[])

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json()

    @staticmethod
    def from_json(data: str) -> "History":
        return History.model_validate_json(data)

    @staticmethod
    def from_dict(data: dict[Any, Any]) -> "History":
        return History.model_validate(data)

    def append(self, event: Event) -> None:
        self.history.append(event)
