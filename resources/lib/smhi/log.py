"""Logging that goes to kodi.log inside Kodi and to stderr outside it."""
import sys

try:
    import xbmc
except ImportError:  # running outside Kodi (tools/run_local.py without stubs)
    xbmc = None

_PREFIX = '[weather.smhi] '


def _log(msg: str, kodi_level: str, name: str) -> None:
    if xbmc is not None:
        xbmc.log(_PREFIX + msg, getattr(xbmc, kodi_level))
    else:
        print(f'{name}: {_PREFIX}{msg}', file=sys.stderr)


def debug(msg: str) -> None: _log(msg, 'LOGDEBUG', 'DEBUG')
def info(msg: str) -> None: _log(msg, 'LOGINFO', 'INFO')
def warning(msg: str) -> None: _log(msg, 'LOGWARNING', 'WARNING')
def error(msg: str) -> None: _log(msg, 'LOGERROR', 'ERROR')
