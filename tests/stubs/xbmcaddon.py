"""Minimal stand-in for Kodi's xbmcaddon module. Settings live in SETTINGS."""
import os
import tempfile

SETTINGS = {}
PROFILE = os.path.join(tempfile.gettempdir(), 'weather.smhi-test-profile')
opened_settings = []


class Addon:
    def __init__(self, addon_id=None):
        self.id = addon_id

    def getSetting(self, key):
        return SETTINGS.get(key, '')

    def setSetting(self, key, value):
        SETTINGS[key] = value

    def getLocalizedString(self, string_id):
        return ''

    def getAddonInfo(self, key):
        return {'profile': PROFILE, 'id': self.id, 'version': '1.0.0'}.get(key, '')

    def openSettings(self):
        opened_settings.append(self.id)
