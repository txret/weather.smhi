"""Minimal stand-in for Kodi's xbmc module (tests and tools/run_local.py)."""
import sys

LOGDEBUG, LOGINFO, LOGWARNING, LOGERROR = 0, 1, 2, 3
_NAMES = {0: 'DEBUG', 1: 'INFO', 2: 'WARNING', 3: 'ERROR'}

# tests may change these
REGION = {
    'tempunit': '°C',
    'speedunit': 'km/h',
    'time': '%H:%M:%S',
    'dateshort': '%Y-%m-%d',
    'datelong': '%A, %d %B %Y',
}
LOG = []
VERBOSE = False
builtins_run = []


def log(msg, level=LOGDEBUG):
    LOG.append((level, msg))
    if VERBOSE or level >= LOGWARNING:
        print(f'{_NAMES.get(level, level)}: {msg}', file=sys.stderr)


def getRegion(key):
    return REGION.get(key, '')


def getLocalizedString(string_id):
    return ''  # not available outside Kodi; callers fall back to English


def executebuiltin(cmd, wait=False):
    builtins_run.append(cmd)
