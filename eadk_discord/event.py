from datetime import date as Date  # noqa: N812
from datetime import datetime as DateTime  # noqa: N812

from pydantic import BaseModel, Field


class SetNumDesks(BaseModel):
    date: Date = Field()
    num_desks: int = Field(ge=0)


class BookDesk(BaseModel):
    date: Date = Field()
    desk_index: int = Field(ge=0)
    user: str = Field(min_length=1)


class UnbookDesk(BaseModel):
    date: Date = Field()
    desk_index: int = Field(ge=0)


class MakeOwned(BaseModel):
    start_date: Date = Field()
    desk_index: int = Field(ge=0)
    user: str = Field(min_length=1)


class MakeFlex(BaseModel):
    start_date: Date = Field()
    desk_index: int = Field(ge=0)


class Event(BaseModel):
    author: str | None = Field()
    time: DateTime = Field()
    event: SetNumDesks | BookDesk | UnbookDesk | MakeOwned | MakeFlex = Field()
