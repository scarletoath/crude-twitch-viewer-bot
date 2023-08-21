from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import TYPE_CHECKING

from .utils import InstanceCommands

if TYPE_CHECKING:
    from .manager import InstanceManager
    from .instance import Instance

logger = logging.getLogger(__name__)


class RestartChecker:
    def __init__(self, restart_interval_s: int = 600):
        self.restart_interval_s = restart_interval_s
        self.worker_thread = None
        self.abort = False
        self.sleep_time = restart_interval_s

    def start(self, manager: InstanceManager):
        if manager is None:
            logger.warning("Unable to start Restarter as manager is None.")
            return

        if not self.worker_thread or not self.worker_thread.is_alive():
            logger.info("Restarter enabled.")
            self.worker_thread = threading.Thread(target=self._restart_loop, args=(manager,), daemon=True)
            self.worker_thread.start()

    def stop(self):
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Restarter disabled.")
            self.abort = True

    @staticmethod
    def get_oldest_instance(manager: InstanceManager) -> Instance:
        return min(manager.browser_instances.values(), key=lambda instance: instance.last_restart_dt)

    def _restart_loop(self, manager: InstanceManager):
        while True:
            time.sleep(self.sleep_time)

            instances_count = manager.instances_alive_count
            if instances_count > 0:
                self.sleep_time = self.restart_interval_s / instances_count
            else:
                logger.warning("Restarter detected zero instances during loop - forcing stop now")
                self.stop()

            if self.abort:
                self.abort = False
                return

            try:
                instance = self.get_oldest_instance(manager)
            except ValueError as e:
                logger.exception(e)
                continue
            logger.info(f"Restarting oldest instance {instance.id}. Restart interval: {self.sleep_time}")
            instance.set_command(InstanceCommands.RESTART)
