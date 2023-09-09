import datetime
import logging
import os
import platform
import random
import threading
import time

from . import logger_config, utils, sites

logger_config.setup()
from .proxy import ProxyGetter
from .screen import Screen
from .service import RestartChecker
from .utils import InstanceCommands

logger = logging.getLogger(__name__)


class InstanceManager:
    def __init__(
        self,
        spawn_thread_count,
        delete_thread_count,
        headless,
        auto_restart,
        proxy_file_name,
        spawn_interval_seconds=2,
        target_url=None,
        restart_checker: RestartChecker = None,
    ):
        logger.info(f"Manager start on {platform.platform()}")

        self._spawn_thread_count = spawn_thread_count
        self._delete_thread_count = delete_thread_count
        self._headless = headless
        self._auto_restart = auto_restart
        self._stop_auto_spawn_event = None
        self.proxies = ProxyGetter(os.path.join(os.getcwd(), "proxy", proxy_file_name))
        self.spawn_interval_seconds = spawn_interval_seconds
        self.target_url = target_url

        self.manager_lock = threading.Lock()
        self._auto_spawn_lock = threading.Lock()
        self.screen = Screen(window_width=500, window_height=300)
        self.user_agents_list = self.get_user_agents()
        self.browser_instances = {}

        self.instances_overview = dict()
        self.instances_alive_count = 0
        self.instances_watching_count = 0

        self.restart_checker = restart_checker

    @property
    def count(self) -> int:
        return len(self.browser_instances)

    def get_user_agents(self):
        try:
            with open(os.path.join(os.getcwd(), "proxy/user-agents.txt")) as user_agents:
                return user_agents.read().splitlines()
        except Exception as e:
            logger.exception(e)
            raise FileNotFoundError()

    def get_headless(self) -> bool:
        return self._headless

    def set_headless(self, new_value: bool):
        self._headless = new_value

    def get_auto_restart(self) -> bool:
        return self._auto_restart

    def set_auto_restart(self, new_value: bool):
        logger.info(f"Setting auto-restart to " + str(new_value))
        self._auto_restart = new_value
        self.reconfigure_auto_restart_status()

    def refresh_proxies(self):
        if self.proxies is not None:
            self.proxies.refresh()

    def __del__(self):
        self.end_auto_spawn()
        print("Deleting manager: cleaning up instances", datetime.datetime.now())
        self.delete_all_instances()
        print("Manager shutting down", datetime.datetime.now())

    def get_random_user_agent(self):
        return random.choice(self.user_agents_list)

    @property
    def isAutoSpawning(self):
        return self._stop_auto_spawn_event is not None

    def begin_auto_spawn(self, max_target, target_url=None):
        if self._stop_auto_spawn_event is not None:
            if self._stop_auto_spawn_event.isSet():
                logger.guiOnly(f"Waiting for previous auto spawn to be stopped ...")
                with self._auto_spawn_lock:
                    pass
            else: # Trying to start auto before stopping previous -> shouldn't happen but just in case
                logger.guiOnly(f"Cannot start another auto spawn session. Stop the previous session first.")
                return

        with self._auto_spawn_lock:
            logger.guiOnly(f"Starting auto spawn with target of {max_target}")
            logger.info(f"Starting auto spawn with target of {max_target}")
            stop_event = self._stop_auto_spawn_event = threading.Event()
        
        def auto_spawn_loop():
            cond = threading.Condition()

            while True:
                # check for instance count and spawn if needed
                should_spawn = self.instances_watching_count < max_target and self.instances_alive_count < max_target
                #print(f"watch={self.instances_watching_count} target={max_target} spawn={should_spawn}")

                if should_spawn:
                    self.spawn_instance(target_url)

                # wait for interval or stop request
                with cond:
                    cond.wait_for(stop_event.isSet, self.spawn_interval_seconds)
                    pass

                if stop_event.isSet():
                    logger.guiOnly("Auto spawn stopped")
                    break

        threading.Thread(target=auto_spawn_loop).start()

    def end_auto_spawn(self):
        if self._stop_auto_spawn_event is not None:
            with self._auto_spawn_lock:
                logger.guiOnly("Stopping auto spawn")
                logger.info("Stopping auto spawn")
                self._stop_auto_spawn_event.set()
                self._stop_auto_spawn_event = None

    def _auto_spawn_monitor(self):
        pass

    def update_instances_alive_count(self):
        alive_instances = filter(
            lambda instance: instance.status != utils.InstanceStatus.SHUTDOWN, self.browser_instances.values()
        )
        self.instances_alive_count = len(list(alive_instances))

    def reconfigure_auto_restart_status(self):
        if self.restart_checker is None:
            return

        if self.instances_alive_count and self._auto_restart:
            self.restart_checker.start(self)
        else:
            self.restart_checker.stop()

    def update_instances_watching_count(self):
        self.instances_watching_count = len(
            [1 for instance in self.browser_instances.values() if instance.status == utils.InstanceStatus.WATCHING]
        )

    def update_instances_overview(self):
        new_overview = {}
        for instance_id, instance in self.browser_instances.items():
            if instance.status != utils.InstanceStatus.SHUTDOWN:
                new_overview[instance_id] = instance.status

        self.instances_overview = new_overview

    def spawn_instances(self, n, target_url=None):
        for _ in range(n):
            self.spawn_instance(target_url)
            time.sleep(self.spawn_interval_seconds)

    def get_site_class(self, target_url):
        for site_name, site_class in utils.supported_sites.items():
            if site_name in target_url:
                return site_class

        return sites.Unknown

    def spawn_instance(self, target_url=None):
        if not self.browser_instances:
            browser_instance_id = 1
        else:
            browser_instance_id = max(self.browser_instances.keys()) + 1

        t = threading.Thread(
            target=self.spawn_instance_thread,
            args=(target_url, self.instance_status_report_callback, browser_instance_id),
            daemon=True,
        )
        t.start()

    def instance_status_report_callback(self, instance_id, instance_status):
        # self.instances_overview[instance_id] = instance_status
        # for now simply triggers the manager to refresh status for all instances
        # maybe track status in separate list, where instances report to
        # and shutdown instances issue remove on dict with instance id
        # his would allow the removal of "instance.status != "shutdown"" in update_instances_alive_count

        logger.info(f"{instance_status.value.upper()} instance {instance_id}")

        self.update_instances_overview()
        self.update_instances_alive_count()
        self.update_instances_watching_count()
        self.reconfigure_auto_restart_status()

    def spawn_instance_thread(self, target_url, status_reporter, browser_instance_id):
        if not any([target_url, self.target_url]):
            raise Exception("No target target url provided")

        if not target_url:
            target_url = self.target_url

        with self.manager_lock:
            user_agent = self.get_random_user_agent()
            proxy = self.proxies.get_proxy_as_dict()

            if self._headless:
                screen_location = self.screen.get_default_location()
            else:
                screen_location = self.screen.get_free_screen_location()

            if not screen_location:
                logger.guiOnly("no screen space left")
                return

            site_class = self.get_site_class(target_url)

            server_ip = proxy.get("server", "no proxy")
            logger.info(
                f"Ordered {site_class.name} instance {browser_instance_id}, {threading.currentThread().name}, proxy {server_ip}, user_agent {user_agent}"
            )

            browser_instance = site_class(
                user_agent,
                proxy,
                target_url,
                status_reporter,
                location_info=screen_location,
                headless=self._headless,
                auto_restart=self._auto_restart,
                instance_id=browser_instance_id,
            )

            self.browser_instances[browser_instance_id] = browser_instance

        browser_instance.start()

        if browser_instance_id in self.browser_instances:
            del browser_instance
            self.browser_instances.pop(browser_instance_id)

    def queue_command(self, instance_id: int, command: InstanceCommands) -> bool:
        if instance_id not in self.browser_instances:
            return False

        self.browser_instances[instance_id].set_command(command)

    def delete_latest(self):
        if not self.browser_instances:
            logger.guiOnly("No instances found")
            return

        latest_key = max(self.browser_instances.keys())
        self.delete_specific(latest_key)

    def delete_specific(self, instance_id):
        if instance_id not in self.browser_instances:
            logger.guiOnly(f"Instance ID {instance_id} not found. Unable to shutdown.")
            return

        instance = self.browser_instances[instance_id]
        logger.guiOnly(f"Issuing shutdown of instance #{instance_id}")
        instance.set_command(InstanceCommands.EXIT)

    def delete_all_instances(self):
        for instance_id in self.browser_instances:
            self.delete_specific(instance_id)

    def restart_all_instances(self, refresh:bool=False):
        command = InstanceCommands.REFRESH if refresh else InstanceCommands.RESTART

        for instance_id in self.browser_instances:
            instance = self.browser_instances[instance_id]
            logger.guiOnly(f"Issuing {command.name.lower()} of instance #{instance_id}")
            instance.set_command(command)
