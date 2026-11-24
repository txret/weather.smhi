"""Command dispatch for default.py.

Invocations:
  default.py <n>                    Kodi weather fetch for location index n (1-based)
  default.py stations <slot>        settings button: edit the observation stations
  default.py pick <slot> <role>     settings button: choose a station
  default.py clear <slot> <role>    settings button: clear a station
where role is forecast.
"""
from __future__ import annotations

import traceback

from . import config, kodi, log, provider


def weather(index: int) -> None:
    slots, slot = provider.location_for_index(kodi.get_setting, index)
    kodi.write_locations([s.name for s in slots], config.SLOTS)
    if slot is None:
        log.warning(f'location {index} is not configured ({len(slots)} configured)')
        kodi.write_props({'WeatherProvider': 'SMHI'})
        return
    values = provider.fetch(slot, kodi.KodiFormatter())
    if values is not None:
        kodi.write_props(values)


def main(argv: list[str]) -> None:
    """Never raises: a traceback would surface as a Kodi error dialog."""
    try:
        args = argv[1:]
        if args and args[0].isdigit():
            weather(int(args[0]))
        elif len(args) == 2 and args[0] == 'stations' and args[1].isdigit():
            from . import settings_ui
            settings_ui.edit_stations(int(args[1]))
        elif len(args) == 3 and args[0] in ('pick', 'clear') and args[1].isdigit():
            from . import settings_ui
            settings_ui.run(args[0], int(args[1]), args[2])
        else:
            log.warning(f'unknown arguments: {args}')
    except Exception:
        log.error('unhandled error:\n' + traceback.format_exc())
