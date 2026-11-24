"""Flatten cached point forecasts into one table: a row per (point, step).

Usage: venv/bin/python -I flatten.py raw data.pkl
"""
import glob
import gzip
import json
import os
import sys
from datetime import datetime

import pandas as pd


def parse_time(value: str) -> datetime:
    """ISO 8601 time with a Z suffix -> aware datetime."""
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def rows_of(path: str, run: str):
    """Yield one dict per time step of the cached point forecast at ``path``."""
    # Besides the raw parameters, each row gets the step length (hours) and
    # the lead time since the model run, since the symbol logic may depend on
    # either (precipitation is an amount over the step, not a rate).
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        doc = json.load(f)
    lon, lat = doc['geometry']['coordinates'][:2]
    ref = parse_time(doc['referenceTime'])
    point = int(os.path.basename(path).split('.')[0])
    for ts in doc['timeSeries']:
        t = parse_time(ts['time'])
        start = parse_time(ts['intervalParametersStartTime'])
        yield {
            'run': run, 'point': point, 'lon': lon, 'lat': lat, 'time': t,
            'hours': (t - start).total_seconds() / 3600,
            'lead': (t - ref).total_seconds() / 3600,
            **ts['data'],
        }


def main(raw_dir: str, out: str) -> None:
    """Read every cached point of every run and write a pickled DataFrame."""
    rows = []
    for run_dir in sorted(glob.glob(os.path.join(raw_dir, 'points', '*'))):
        run = os.path.basename(run_dir)
        for path in glob.glob(os.path.join(run_dir, '*.json.gz')):
            rows.extend(rows_of(path, run))
    df = pd.DataFrame(rows)
    df.to_pickle(out)
    print(f'{len(df)} rows, {df.point.nunique()} points, runs {sorted(df.run.unique())}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
