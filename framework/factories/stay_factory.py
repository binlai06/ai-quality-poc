"""Builds exact stay dates far in the future, so tests do not collide with other data."""

from datetime import date, timedelta

from framework.models.booking import Stay


class StayFactory:
    """Creates stays counted in days from a base date that is FAR_FUTURE_DAYS after today."""

    FAR_FUTURE_DAYS = 400

    @classmethod
    def build(cls, first_day: int, last_day: int) -> Stay:
        """A stay from day `first_day` to day `last_day`, both counted from the base date.

        Day 0 is the base date, so `build(10, 15)` checks in on day 10 and out on day 15.
        """
        base = date.today() + timedelta(days=cls.FAR_FUTURE_DAYS)
        return Stay(
            checkin=base + timedelta(days=first_day),
            checkout=base + timedelta(days=last_day),
        )
