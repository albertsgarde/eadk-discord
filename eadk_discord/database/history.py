from datetime import date as Date  # noqa: N812

from beartype import beartype
from beartype.typing import Any  # noqa: N812
from pydantic import BaseModel, Field

from .event import Event


class History(BaseModel):
    start_date: Date = Field()
    history: list[Event] = Field()

    @staticmethod
    def initialize(start_date: Date) -> "History":
        return History(start_date=start_date, history=[])

    def to_dict(self) -> dict[str, Any]:  # pragma: no cover
        return self.model_dump()

    def to_json(self) -> str:  # pragma: no cover
        return self.model_dump_json()

    @beartype
    @staticmethod
    def from_json(data: str) -> "History":  # pragma: no cover
        return History.model_validate_json(data)

    @beartype
    @staticmethod
    def from_dict(data: dict[Any, Any]) -> "History":  # pragma: no cover
        return History.model_validate(data)

    @beartype
    def append(self, event: Event) -> None:
        self.history.append(event)
