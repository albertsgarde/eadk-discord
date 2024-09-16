import datetime
from datetime import date, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

MAX_FUTURE_DAYS: int = 366


class DeskStatus(BaseModel):
    booked: str | None = Field()

    def is_booked(self) -> bool:
        """
        Returns True if the desk is booked, False if the desk is not booked.
        """
        return self.booked is not None

    def booked_by(self) -> str | None:
        """
        Returns the user who booked the desk, or None if the desk is not booked.
        """
        return self.booked

    def book(self, user: str) -> bool:
        """
        Returns True if the desk was successfully booked, False if the desk was already booked.
        """
        if self.is_booked():
            return False
        else:
            self.booked = user
            return True


class Day(BaseModel):
    date: datetime.date = Field()
    desks: list[DeskStatus] = Field()

    @classmethod
    def create_unbooked(cls, date: datetime.date, num_desks: int) -> "Day":
        return cls(date=date, desks=[DeskStatus(booked=None) for _ in range(num_desks)])

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
            if not desk.is_booked():
                return i
        return None

    def available_desks(self) -> list[int]:
        """
        Returns a list of indices of available desks.
        """
        return [i for i, desk in enumerate(self.desks) if not desk.is_booked()]


class Database(BaseModel):
    start_date: date = Field()
    days: list[Day] = Field()

    @staticmethod
    def load_or_create(path: Path, start_date: date, starting_days: int, num_desks: int) -> "Database":
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
    def create(start_date: date, starting_days: int, num_desks: int) -> "Database":
        """
        Creates a new database with the given start date, number of days, and number of desks.
        Will be initialized with `starting_days` days, each with `num_desks` unbooked desks.
        """
        if starting_days <= 0:
            raise ValueError("the database must start with at least one day")
        start_date = start_date
        days = [Day.create_unbooked(start_date + timedelta(i), num_desks) for i in range(starting_days)]
        return Database(start_date=start_date, days=days)

    def save(self, path: Path):
        """
        Saves the database to the given path.
        """
        with path.open("w") as file:
            file.write(self.model_dump_json())

    def day(self, date_arg: date) -> Day | None:
        """
        Returns the Day object for the given date, or None if the date is not in the database.
        """
        days_from_start_date = (date_arg - self.start_date).days
        if days_from_start_date < 0:
            return None
        elif days_from_start_date >= len(self.days):
            days_from_now = (date_arg - date.today()).days
            if days_from_now <= MAX_FUTURE_DAYS:
                cur_max_from_now = (self.days[-1].date - date.today()).days
                self.days.extend(
                    [
                        Day.create_unbooked(date.today() + timedelta(i), len(self.days[-1].desks))
                        for i in range(cur_max_from_now + 1, days_from_now + 1)
                    ]
                )
                return self.days[days_from_start_date]
        else:
            return self.days[days_from_start_date]
