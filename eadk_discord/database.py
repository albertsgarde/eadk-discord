from dataclasses import dataclass
from datetime import date as Date  # noqa: N812
from datetime import timedelta as TimeDelta  # noqa: N812
from pathlib import Path

from pydantic import BaseModel, Field

MAX_FUTURE_DAYS: int = 366


class DeskStatus(BaseModel):
    booker: str | None = Field()
    owner: str | None = Field()

    def book(self, user: str) -> bool:
        """
        Returns True if the desk was successfully booked, False if the desk was already booked.
        """
        if self.booker:
            return False
        else:
            self.booker = user
            return True

    def unbook(self) -> bool:
        """
        Returns True if the desk was successfully unbooked, False if the desk was not booked.
        """
        if self.booker:
            self.booker = None
            return True
        else:
            return False

    def make_owned(self, desk: int, user: str) -> bool:
        """
        Returns True if the desk was successfully permanently booked, False if the desk was already permanently booked.
        """
        if self.owner:
            return False
        else:
            if self.booker is None:
                self.booker = user
            self.owner = user
            return True

    def make_flex(self, desk: int) -> bool:
        """
        Returns True if the desk was successfully unpermanently booked, False if the desk was not permanently booked.
        """
        if self.owner:
            if self.owner == self.booker:
                self.booker = None
            self.owner = None
            return True
        else:
            return False


class Day(BaseModel):
    date: Date = Field()
    desks: list[DeskStatus] = Field()

    @classmethod
    def create_unbooked(cls, date: Date, num_desks: int) -> "Day":
        return cls(date=date, desks=[DeskStatus(booker=None, owner=None) for _ in range(num_desks)])

    @classmethod
    def create_from_previous(cls, previous: "Day") -> "Day":
        return cls(
            date=previous.date + TimeDelta(1),
            desks=[DeskStatus(booker=desk.owner, owner=desk.owner) for desk in previous.desks],
        )

    def desk(self, desk: int) -> DeskStatus:
        """
        Returns the DeskStatus object for the given desk.
        """
        if desk < 0:
            raise ValueError("desk number must be non-negative")
        elif desk >= len(self.desks):
            raise ValueError("desk number is out of range. There are only {len(self.desks)} desks.")
        return self.desks[desk]

    def get_available_desk(self) -> int | None:
        """
        Returns the first available desk, or None if all desks are booked.
        """
        for i, desk in enumerate(self.desks):
            if desk.booker is None:
                return i
        return None

    def available_desks(self) -> list[int]:
        """
        Returns a list of indices of available desks.
        """
        return [i for i, desk in enumerate(self.desks) if desk.booker is None]

    def booked_desks(self, member: str) -> list[int]:
        """
        Returns the index of the desk booked by the given member, or None if the member has not booked a desk.
        """
        return [i for i, desk in enumerate(self.desks) if desk.booker == member]


@dataclass
class DeskAlreadyOwnedError(Exception):
    owner: str
    desk: int
    day: Date


class Database(BaseModel):
    start_date: Date = Field()
    days: list[Day] = Field()

    @staticmethod
    def load_or_create(path: Path, start_date: Date, starting_days: int, num_desks: int) -> "Database":
        """
        Loads the database from the given path, or creates a new database if the path does not exist.
        """
        try:
            database = Database.load(path)
            print(f"Loaded database from {path}.")
        except FileNotFoundError:
            database = Database.create(start_date, starting_days, num_desks)
            print(f"No database found at {path}, created new database.")
        return database

    @staticmethod
    def load(path: Path) -> "Database":
        """
        Loads the database from the given path.
        Throws an exception either if file doesn't exist or the file exists but is not a valid database.
        """
        with path.open("r") as file:
            return Database.model_validate_json(file.read())

    @staticmethod
    def create(start_date: Date, starting_days: int, num_desks: int) -> "Database":
        """
        Creates a new database with the given start date, number of days, and number of desks.
        Will be initialized with `starting_days` days, each with `num_desks` unbooked desks.
        """
        if starting_days <= 0:
            raise ValueError("the database must start with at least one day")
        first_day = Day.create_unbooked(start_date, num_desks)
        days = [first_day]
        while len(days) < starting_days:
            days.append(Day.create_from_previous(days[-1]))
        return Database(start_date=start_date, days=days)

    def save(self, path: Path):
        """
        Saves the database to the given path.
        """
        with path.open("w") as file:
            file.write(self.model_dump_json())

    def day(self, date: Date) -> Day | None:
        """
        Returns the Day object for the given date, or None if the date is not in the database.
        """
        days_from_start_date = (date - self.start_date).days
        today_max_date_index = days_from_start_date + MAX_FUTURE_DAYS
        if days_from_start_date < 0:
            return None
        while len(self.days) <= min(days_from_start_date, today_max_date_index):
            self.days.append(Day.create_from_previous(self.days[-1]))
        if len(self.days) <= days_from_start_date:
            return None
        return self.days[days_from_start_date]

    def make_owned(self, date: Date, desk: int, user: str) -> None:
        day_index = (date - self.start_date).days
        day = self.day(date)
        if day is None:
            return None
        desk_owner = day.desk(desk).owner
        if desk_owner:
            raise DeskAlreadyOwnedError(owner=desk_owner, desk=desk, day=date)
        days = self.days[day_index:]
        for day in days:
            day.desk(desk).make_owned(desk, user)

    def make_flex(self, date: Date, desk: int) -> None:
        day_index = (date - self.start_date).days
        if self.day(date) is None:
            return None
        days = self.days[day_index:]
        for day in days:
            try:
                day.desk(desk).make_flex(desk)
            except ValueError:
                break
