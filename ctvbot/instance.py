from __future__ import annotations

import datetime
import logging
import threading

from playwright.sync_api import sync_playwright
from abc import ABC


from . import utils

logger = logging.getLogger(__name__)


class Instance(ABC):
    _browser_type = "chromium"
    _browser_path = None

    # Timeouts in milliseconds
    _timeout_buffer = 1000
    _timeout_retry  = 20000
    _timeout_reload = 30000
    _timeout_wait   = 10000
    _max_tries      = 3
    _loc_width      = 500
    _loc_height     = 300

    @staticmethod
    def config_browser(type, path=None):
        Instance._browser_type = type
        Instance._browser_path = path if path else None

    @staticmethod
    def configure(retrySeconds:int = None, reloadSeconds:int = None, waitSeconds:int = None, getConfigValue:function = None):
        Instance._timeout_retry  = retrySeconds  * 1000 if retrySeconds  is not None else Instance._timeout_retry
        Instance._timeout_reload = reloadSeconds * 1000 if reloadSeconds is not None else Instance._timeout_reload
        Instance._timeout_wait   = waitSeconds   * 1000 if waitSeconds   is not None else Instance._timeout_wait

        if getConfigValue is None: # No extractor provided to get site-specific config -> early out
            return

        Instance._timeout_buffer = getConfigValue("timeout.buffer", fallback=1) * 1000

        Instance._max_tries  = getConfigValue("maxTries", fallback=3)
        Instance._loc_width  = getConfigValue("width",    fallback=500)
        Instance._loc_height = getConfigValue("height",   fallback=300)

        # Enumerate derived classes and try to config if possible
        derived_instance_types = Instance.__subclasses__()
        for derived_instance_type in derived_instance_types:
            foundEx =  None
            try:
                derived_instance_type._configure(lambda key, fallback:getConfigValue(f"{derived_instance_type.__name__}.{key}", fallback=fallback)) # prefix key with site name
                logger.info(f"Loaded site-specific config for Instance->{derived_instance_type.__name__}")
            except AttributeError as ex:
                if "_configure" not in ex.args[0]: # Expected _configure() not found if not defined in derived class; any other attribute is true error
                    foundEx = ex
            except Exception as ex:
                foundEx = ex
            finally:
                if foundEx is not None:
                    logger.exception(f"Exception while extracting site-specific config for Instance->{derived_instance_type.__name__}.", exc_info=foundEx)

    name = "BASE"
    instance_lock = threading.Lock()

    def __init__(
        self,
        user_agent,
        proxy_dict,
        target_url,
        status_reporter,
        location_info=None,
        headless=False,
        auto_restart=False,
        instance_id=-1,
    ):
        self.playwright = None
        self.context = None
        self.browser = None
        self.status_info = {}
        self.status_reporter = status_reporter
        self.thread = threading.current_thread()

        self.id = instance_id
        self._status = "alive"
        self.user_agent = user_agent
        self.proxy_dict = proxy_dict
        self.target_url = target_url
        self.headless = headless
        self.auto_restart = auto_restart

        self.last_restart_dt = datetime.datetime.now()

        self.location_info = location_info
        if not self.location_info:
            self.location_info = {
                "index": -1,
                "x": 0,
                "y": 0,
                "width": Instance._loc_width,
                "height": Instance._loc_height,
                "free": True,
            }

        self._command = None
        self.page = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, new_status):
        if self._status == new_status:
            return

        self._status = new_status
        self.status_reporter(self.id, new_status)

    def set_command(self, new_command: utils.InstanceCommands):
        if self._command == new_command:
            return

        self._command = new_command
        if new_command == utils.InstanceCommands.RESTART:
            self.last_restart_dt = datetime.datetime.now()

    def clean_up_playwright(self):
        if any([self.page, self.context, self.browser]):
            self.page.close()
            self.context.close()
            self.browser.close()
            self.playwright.stop()

    def start(self):
        try:
            self.spawn_page()
            self.todo_after_spawn()
            self.loop_and_check()
        except Exception as e:
            message = e.args[0][:25] if e.args else ""
            name = f"{self.name} Instance {self.id}"
            logger.exception(f"{name} died at page '{self.page.url if self.page else None}'", exc_info=e)
            logger.guiOnly(f"{name} died: {type(e).__name__}:{message}... Please see ctvbot.log.")
        else:
            logger.info(f"ENDED: instance {self.id}")
            with self.instance_lock:
                logger.guiOnly(f"Instance {self.id} shutting down")
        finally:
            self.status = utils.InstanceStatus.SHUTDOWN
            self.clean_up_playwright()
            self.location_info["free"] = True

    def loop_and_check(self):
        page_timeout_s = Instance._timeout_wait
        while True:
            self.page.wait_for_timeout(page_timeout_s)
            self.todo_every_loop()
            self.update_status()

            if self._command == utils.InstanceCommands.RESTART:
                self.clean_up_playwright()
                self.spawn_page(restart=True)
                self.todo_after_spawn()
            if self._command == utils.InstanceCommands.SCREENSHOT:
                logger.guiOnly(f"Saved screenshot of instance id {self.id}")
                self.save_screenshot()
            if self._command == utils.InstanceCommands.REFRESH:
                logger.guiOnly(f"Manual refresh of instance id {self.id}")
                self.reload_page()
            if self._command == utils.InstanceCommands.EXIT:
                return
            self._command = utils.InstanceCommands.NONE

    def save_screenshot(self):
        filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + f"_instance{self.id}.png"
        self.page.screenshot(path=filename)

    def spawn_page(self, restart=False):
        proxy_dict = self.proxy_dict

        self.status = utils.InstanceStatus.RESTARTING if restart else utils.InstanceStatus.STARTING

        if not proxy_dict:
            proxy_dict = None

        self.playwright = sync_playwright().start()

        browser_type = self.playwright.chromium # default to chromium if not specified
        if Instance._browser_type == "chromium":
            browser_type = self.playwright.chromium
        elif Instance._browser_type == "firefox":
            browser_type = self.playwright.firefox
        elif Instance._browser_type == "webkit":
            browser_type = self.playwright.webkit

        self.browser = browser_type.launch(
            proxy=proxy_dict,
            headless=self.headless,
            executable_path=Instance._browser_path,
            channel="chrome",
            args=[
                "--window-position={},{}".format(self.location_info["x"], self.location_info["y"]),
                "--mute-audio",
            ],
        )
        self.context = self.browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": 800, "height": 600},
            proxy=proxy_dict,
        )

        self.page = self.context.new_page()
        self.page.add_init_script("""navigator.webdriver = false;""")

    def goto_with_retry(self, url, max_tries=None, timeout=None):
        """
        Tries to navigate to a page max_tries times. Raises the last exception if all attempts fail.
        """
        timeout = timeout if timeout is not None else Instance._timeout_retry
        max_tries = max_tries if max_tries is not None else Instance._max_tries
        for attempt in range(1, max_tries + 1):
            try:
                self.page.goto(url, timeout=timeout)
                return
            except Exception as e:
                logger.warning(f"Instance {self.id} failed connection attempt #{attempt} with timeout of {timeout}ms.")
                if attempt == max_tries:
                    raise

    def todo_after_load(self):
        self.goto_with_retry(self.target_url)
        self.page.wait_for_timeout(Instance._timeout_buffer)

    def reload_page(self):
        self.page.reload(timeout=Instance._timeout_reload)
        self.todo_after_load()

    def todo_after_spawn(self):
        """
        Basic behaviour after a page is spawned. Override for more functionality
        e.g. load cookies, additional checks before instance is truly called "initialized"
        :return:
        """
        self.status = utils.InstanceStatus.INITIALIZED
        self.goto_with_retry(self.target_url)

    def todo_every_loop(self):
        """
        Add behaviour to be executed every loop
        e.g. to fake page interaction to not count as inactive to the website.
        """
        pass

    def update_status(self) -> None:
        """
        Mechanism is called every loop. Figure out if it is watching and working and updated status.
        if X:
            self.status = utils.InstanceStatus.WATCHING
        """
        pass
