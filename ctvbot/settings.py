import logging
import os
import configparser

logger = logging.getLogger(__name__)


class Settings:
    def __init__(self, settings_file_name="settings.ini"):
        self._settings = {}
        self.pathed_file_name = os.path.join(os.getcwd(), "config", proxy_file_name)
        self.load_settings()

    @property
    def General(self):
        return self._settings['General']

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read(self.pathed_file_name)
        self._settings = config.sections()
