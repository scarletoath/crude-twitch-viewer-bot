import logging
import os
import configparser

logger = logging.getLogger(__name__)


class Settings:
    def __init__(self, settings_file_name="settings.ini"):
        self._config = configparser.ConfigParser()
        self.pathed_file_name = os.path.join(os.getcwd(), "config", settings_file_name)
        self.load_settings()

    @property
    def General(self):
        return self._config['General']

    @property
    def Instance(self):
        return self._config['Instance']

    @property
    def Window(self):
        return self._config['Window']

    @property
    def Browsers(self):
        return self._config['Browsers']

    def load_settings(self):
        config = self._config
        config.read(self.pathed_file_name)

    def save_settings(self):
        with open(self.pathed_file_name, 'w') as configFile:
            self._config.write(configFile, space_around_delimiters=False)
