#!/usr/bin/env python3
"""Fetch live SMHI data the same way Kodi would and print the window
properties. Uses the stub xbmc modules in tests/stubs, so Kodi is not needed.

Examples:
    python tools/run_local.py --station 98230 --station 97200
    python tools/run_local.py --lat 67.85 --lon 20.23 --name Kiruna
    python tools/run_local.py --stations          # list active stations
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'stubs'))
sys.path.insert(0, os.path.join(ROOT, 'resources', 'lib'))
sys.path.insert(0, ROOT)

import xbmc  # noqa: E402  (stub)
import xbmcaddon  # noqa: E402  (stub)
import xbmcgui  # noqa: E402  (stub)


def main():
    """Configure location 1 from the command line, run a fetch and print the
    resulting window properties."""
    # The stub xbmcaddon.SETTINGS dict stands in for the add-on settings, so
    # this writes the same keys the settings picker would and then runs the
    # real entry point. Station names and positions come from SMHI's station
    # list, which the forecast point (first station's position) relies on.
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--station', action='append', default=[],
                    help='observation station id; repeat for up to 5 stations in priority order')
    ap.add_argument('--lat', help='custom forecast latitude')
    ap.add_argument('--lon', help='custom forecast longitude')
    ap.add_argument('--name', help='location name')
    ap.add_argument('--stations', action='store_true', help='list active stations and exit')
    ap.add_argument('--tempunit', default='°C')
    ap.add_argument('--speedunit', default='km/h')
    ap.add_argument('-v', '--verbose', action='store_true', help='show debug log')
    args = ap.parse_args()

    xbmc.VERBOSE = args.verbose
    xbmc.REGION.update(tempunit=args.tempunit, speedunit=args.speedunit)
    from smhi import config, observations
    if len(args.station) > config.STATIONS:
        ap.error(f'at most {config.STATIONS} --station options')

    if args.stations:
        for s in observations.list_stations() or []:
            print(f'{s.id:>7}  {s.lat:8.4f} {s.lon:8.4f}  {s.name}')
        return

    settings = xbmcaddon.SETTINGS
    if args.name:
        settings['loc1_name'] = args.name
    # station rows in the order given, as the settings picker would write them
    known = {s.id: s for s in observations.list_stations() or []} if args.station else {}
    for role, sid in zip(config.STATION_ROLES, args.station):
        settings[f'loc1_{role}_id'] = sid
        if st := known.get(sid):
            settings[f'loc1_{role}_name'] = st.name
            settings[f'loc1_{role}_lat'] = str(st.lat)
            settings[f'loc1_{role}_lon'] = str(st.lon)
    if args.lat and args.lon:
        settings.update(loc1_fc_source='2', loc1_lat=args.lat, loc1_lon=args.lon)

    import default
    default.main(['default.py', '1'])

    props = xbmcgui.Window(12600).props
    if not props.get('Current.IsFetched'):
        print('no current weather fetched', file=sys.stderr)
    for k in sorted(props, key=_sort_key):
        print(f'{k} = {props[k]}')


def _sort_key(k):
    # natural sort: Hourly.2 before Hourly.10
    return [(0, int(p), '') if p.isdigit() else (1, 0, p) for p in re.split(r'[.]|(?<=Day)(?=\d)', k)]


if __name__ == '__main__':
    main()
