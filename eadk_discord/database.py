import datetime
from datetime import date, timedelta
from pathlib import Path

from pydantic import BaseModel, Field


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
        return self.desks[desk]

    def book(self, desk: int, user: str) -> bool:
        """
        Returns True if the desk was successfully booked, False if the desk was already booked.
        """
        return self.desks[desk].book(user)


class Database(BaseModel):
    start_date: date = Field()
    days: list[Day] = Field()

    @staticmethod
    def load_or_create(path: Path, start_date: date, starting_days: int, num_desks: int) -> "Database":
        """
        Loads the database from the given path, or creates a new database if the path does not exist.
        """
        try:
            return Database.load(path)
        except FileNotFoundError:
            return Database.create(start_date, starting_days, num_desks)

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

    def day(self, date: date) -> Day | None:
        """
        Returns the Day object for the given date, or None if the date is not in the database.
        """
        days_from_start_date = (date - self.start_date).days
        if days_from_start_date < 0 or days_from_start_date >= len(self.days):
            return None
        else:
            return self.days[days_from_start_date]
