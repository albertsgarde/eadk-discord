from datetime import date as Date  # noqa: N812
from datetime import datetime as DateTime  # noqa: N812

from pydantic import BaseModel, Field


class SetNumDesks(BaseModel):
    date: Date = Field()
    num_desks: int = Field()


class BookDesk(BaseModel):
    start_date: Date = Field()
    end_date: Date = Field()
    desk_index: int = Field()
    user: int = Field()


class UnbookDesk(BaseModel):
    start_date: Date = Field()
    end_date: Date = Field()
    desk_index: int = Field()


class MakeOwned(BaseModel):
    start_date: Date = Field()
    desk_index: int = Field()
    user: int = Field()


class MakeFlex(BaseModel):
    start_date: Date = Field()
    desk_index: int = Field()


class Event(BaseModel):
    author: int | None = Field()
    time: DateTime = Field()
    event: SetNumDesks | BookDesk | UnbookDesk | MakeOwned | MakeFlex = Field()
