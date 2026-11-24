"""Fetch everything for one location and turn it into window properties.

Kodi-independent apart from the ``get`` settings callable, so
``tools/run_local.py`` and the tests can drive it directly.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable

from . import config, daily, forecast, log, observations, props
from .model import WxObs, merge


def fetch(slot: config.Slot, fmt: props.Formatter, now: datetime | None = None) -> dict[str, str] | None:
    """Window properties for ``slot``, or None if no data at all could be
    fetched (the caller then leaves the previous properties in place)."""
    # The forecast and every configured station are fetched in parallel (each
    # is several HTTP round trips), then merged field by field in priority
    # order: station 1 -> ... -> station 5 -> forecast for the current hour.
    # Empty station rows are skipped here; stations that return nothing come
    # back as None, which merge() skips too.
    now = now or datetime.now(timezone.utc)

    with ThreadPoolExecutor(max_workers=1 + config.STATIONS) as pool:
        fc_job = (pool.submit(forecast.get_forecast, slot.forecast_lat, slot.forecast_lon)
                  if slot.has_forecast_point else None)
        obs_jobs = [pool.submit(observations.get_station_obs, sid, now)
                    for sid in slot.station_ids if sid]
        steps = fc_job.result() if fc_job else None
        station_obs: list[WxObs | None] = [j.result() for j in obs_jobs]

    if not slot.has_forecast_point:
        log.warning(f'{slot.name}: no forecast point configured')

    # job order matches station priority, so merge() fills gaps sequentially
    current = merge(*station_obs, forecast.step_at(steps, now))
    if current is None:
        log.error(f'{slot.name}: no data from SMHI')
        return None
    days = daily.summarize(steps, now, fmt.tz)
    return props.build(slot.name, current, steps, days, fmt, now)


def location_for_index(get: Callable[[str], str], index: int) -> tuple[list[config.Slot], config.Slot | None]:
    """All configured slots, and the one for Kodi location ``index`` (1-based)
    or None if there is no such location."""
    slots = config.configured_slots(get)
    return slots, slots[index - 1] if 1 <= index <= len(slots) else None
