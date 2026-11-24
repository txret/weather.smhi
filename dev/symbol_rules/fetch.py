"""Download snow1g point forecasts for a random sample of SMHI grid points.

Usage: python3 -I fetch.py raw N_POINTS [SEED]

Grid coordinates come from RAW_DIR/multipoint.json (the snow1g multipoint
geometry). Each point's forecast is cached as RAW_DIR/points/<run>/<idx>.json.gz,
so a rerun only downloads what is missing.
"""
import gzip
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = 'https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1'
POINT_URL = BASE + '/geotype/point/lon/{lon}/lat/{lat}/data.json'
HEADERS = {'User-Agent': 'smhi-symbol-research/0.1', 'Accept-Encoding': 'gzip'}
WORKERS = 4           # stay polite to a free public API
RETRIES = 4


def get(url: str) -> tuple[int, bytes | None]:
    """GET ``url`` and return (status, gzip-compressed body or None)."""
    # Retry with backoff on rate limiting / server errors; 404 means the point
    # is outside the forecast area and is not retried.
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                if r.headers.get('Content-Encoding') != 'gzip':
                    body = gzip.compress(body)
                return r.status, body
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            status = e.code
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            status = 0
        time.sleep(2 ** attempt)
    return status, None


def fetch_point(out_dir: str, idx: int, lon: float, lat: float) -> str:
    """Download one point into ``out_dir`` unless cached; returns a status word."""
    path = os.path.join(out_dir, f'{idx}.json.gz')
    if os.path.exists(path):
        return 'cached'
    status, body = get(POINT_URL.format(lon=round(lon, 6), lat=round(lat, 6)))
    if body is None:
        return f'http {status}'
    with open(path + '.tmp', 'wb') as f:
        f.write(body)
    os.replace(path + '.tmp', path)
    return 'ok'


def main(raw_dir: str, n: int, seed: int = 1) -> None:
    """Sample ``n`` grid points and download their forecasts for the current run."""
    # The current model run is identified by referenceTime; caching per run
    # keeps samples from different runs apart (they describe different weather).
    with open(os.path.join(raw_dir, 'multipoint.json'), encoding='utf-8') as f:
        coords = json.load(f)['coordinates']
    _, run_body = get(BASE + '/createdtime.json')
    run = json.loads(gzip.decompress(run_body))['referenceTime'].replace(':', '')
    out_dir = os.path.join(raw_dir, 'points', run)
    os.makedirs(out_dir, exist_ok=True)

    rng = random.Random(seed)
    sample = rng.sample(range(len(coords)), n)
    counts: dict[str, int] = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        jobs = [pool.submit(fetch_point, out_dir, i, *coords[i]) for i in sample]
        for k, job in enumerate(jobs, 1):
            word = job.result()
            counts[word] = counts.get(word, 0) + 1
            if k % 100 == 0:
                print(f'{k}/{n} {counts}', flush=True)
    print(f'run {run}: {counts}')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), *(int(a) for a in sys.argv[3:4]))
