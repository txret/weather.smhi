import json
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')
sys.path.insert(0, os.path.join(ROOT, 'tests', 'stubs'))
sys.path.insert(0, os.path.join(ROOT, 'resources', 'lib'))
sys.path.insert(0, ROOT)

# Time the fixtures were recorded: observations at 12:00Z, forecast from 13:00Z
NOW = datetime(2026, 11, 9, 12, 30, tzinfo=timezone.utc)
STOCKHOLM = ZoneInfo('Europe/Stockholm')


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def fake_http(monkeypatch):
    """Serve SMHI URLs from tests/fixtures; anything unknown is a 404.
    Returns the list of requested URLs."""
    from smhi import http
    requested = []

    def get_json(url, timeout=None):
        requested.append(url)
        if '/snow1g/' in url:
            return 200, load_fixture('snow1g_stockholm.json')
        m = re.search(r'/parameter/(\d+)/station/(\d+)/', url)
        if m:
            name = f'metobs_{m.group(2)}_{m.group(1)}.json'
            if os.path.exists(os.path.join(FIXTURES, name)):
                return 200, load_fixture(name)
        m = re.search(r'/parameter/(\d+)/station-set/all/', url)
        if m and m.group(1) == '1':
            return 200, load_fixture('stationset_1.json')
        return 404, None

    monkeypatch.setattr(http, 'get_json', get_json)
    return requested


@pytest.fixture
def kodi_env():
    """Fresh fake Kodi state: settings, weather window, region."""
    import xbmc
    import xbmcaddon
    import xbmcgui
    xbmcaddon.SETTINGS.clear()
    xbmcaddon.opened_settings.clear()
    xbmcgui._WINDOWS.clear()
    xbmcgui.Dialog.reset()
    xbmc.LOG.clear()
    yield xbmcaddon.SETTINGS
    xbmcaddon.SETTINGS.clear()
    xbmcgui._WINDOWS.clear()
