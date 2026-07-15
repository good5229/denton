from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ReleaseRule:
    source: str
    frequency: str
    publication_lag_months: int
    note: str


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(day.day, days[month - 1]))


def period_end(period: str, frequency: str) -> date:
    frequency = frequency.upper()
    if frequency == "A":
        return date(int(period), 12, 31)
    if frequency == "Q":
        year = int(period[:4])
        quarter = int(period[-1])
        month = quarter * 3
        day = 31 if month in {3, 12} else 30
        return date(year, month, day)
    if frequency == "M":
        year = int(period[:4])
        month = int(period[-2:])
        day = 31 if month in {1, 3, 5, 7, 8, 10, 12} else 30
        if month == 2:
            day = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
        return date(year, month, day)
    raise ValueError(f"Unsupported frequency: {frequency}")


def available_date(period: str, frequency: str, publication_lag_months: int) -> date:
    return add_months(period_end(period, frequency), publication_lag_months)


def is_available_as_of(period: str, frequency: str, publication_lag_months: int, as_of: date) -> bool:
    return available_date(period, frequency, publication_lag_months) < as_of


def annual_forecast_origin(target_year: int, month: int = 1, day: int = 1) -> date:
    return date(target_year, month, day)


def quarter_sort_key(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])
