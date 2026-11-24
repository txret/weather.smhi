"""Thin HTTP layer: one shared session, timeouts, never raises."""
from __future__ import annotations

from typing import Any

import requests

from . import __version__, log

USER_AGENT = f'weather.smhi/{__version__} (Kodi weather add-on)'
TIMEOUT = 15  # seconds

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers['User-Agent'] = USER_AGENT
        _session.headers['Accept'] = 'application/json'
    return _session


def get_json(url: str, timeout: float = TIMEOUT) -> tuple[int | None, Any]:
    """GET ``url`` and decode JSON.

    Returns ``(status_code, data)``. ``data`` is None unless the status is 200
    and the body is valid JSON. ``status_code`` is None on network errors.
    """
    try:
        r = session().get(url, timeout=timeout)
    except requests.RequestException as e:
        log.warning(f'request failed: {url}: {e}')
        return None, None
    if r.status_code != 200:
        return r.status_code, None
    try:
        return 200, r.json()
    except ValueError:
        log.warning(f'invalid JSON from {url}')
        return 200, None
