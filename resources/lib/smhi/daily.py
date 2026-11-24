"""Aggregate forecast steps into per-day summaries (local time)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from itertools import groupby

from .model import WxObs
from .symbols import Wsymb2


@dataclass
class DaySummary:
    date: date
    high: float | None
    low: float | None
    symbol: Wsymb2 | None
    precip_amount: float | None   # mm, sum over the day
    wind_speed: float | None      # m/s, max
    wind_degree: int | None       # at the representative step
    humidity: int | None          # %, mean
    representative: WxObs         # step nearest local noon

    @property
    def condition_text(self) -> str | None:
        return self.representative.condition_text


def _midpoint(step: WxObs) -> datetime:
    return step.time - timedelta(hours=(step.interval_hours or 1) / 2)


def summarize(steps: list[WxObs] | None, now: datetime | None = None,
              tz: tzinfo | None = None, max_days: int = 10) -> list[DaySummary]:
    """Group steps by the local date of their interval midpoint. Days before
    today are dropped; day 0 is today."""
    if not steps:
        return []
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(tz).date()

    def local(s: WxObs) -> datetime:
        return _midpoint(s).astimezone(tz)

    days = []
    for day, group in groupby(sorted(steps, key=lambda s: s.time), key=lambda s: local(s).date()):
        if day < today:
            continue
        group = list(group)
        rep = min(group, key=lambda s: abs(local(s).hour + local(s).minute / 60 - 12))
        temps = [s.temperature for s in group if s.temperature is not None]
        amounts = [s.precip_amount for s in group if s.precip_amount is not None]
        winds = [s.wind_speed for s in group if s.wind_speed is not None]
        hums = [s.humidity for s in group if s.humidity is not None]
        days.append(DaySummary(
            date=day,
            high=max(temps) if temps else None,
            low=min(temps) if temps else None,
            symbol=rep.effective_symbol,
            precip_amount=sum(amounts) if amounts else None,
            wind_speed=max(winds) if winds else None,
            wind_degree=rep.wind_degree,
            humidity=round(sum(hums) / len(hums)) if hums else None,
            representative=rep,
        ))
        if len(days) >= max_days:
            break
    return days
