from ctvbot.gui import GUI
from ctvbot.manager import InstanceManager
from ctvbot.settings import Settings
from ctvbot.instance import Instance

settings = Settings()

SPAWNER_THREAD_COUNT   = settings.General.getint("multi_spawn_count", fallback=3)
CLOSER_THREAD_COUNT    = settings.General.getint("closer_thread_count", fallback=10)
PROXY_FILE_NAME        = "proxy_list.txt"
HEADLESS               = settings.General.getboolean("headless", fallback=True)
AUTO_RESTART           = settings.General.getboolean("auto_restart", fallback=True)
SPAWN_INTERVAL_SECONDS = settings.General.getint("spawn_interval", fallback=2)

BROWSER_TYPE = settings.Browsers.get("launch", fallback="chromium")
BROWSER_PATH = settings.Browsers.get(BROWSER_TYPE, fallback=None)

Instance.config_browser(BROWSER_TYPE, BROWSER_PATH)

manager = InstanceManager(
    spawn_thread_count=SPAWNER_THREAD_COUNT,
    delete_thread_count=CLOSER_THREAD_COUNT,
    headless=HEADLESS,
    auto_restart=AUTO_RESTART,
    proxy_file_name=PROXY_FILE_NAME,
    spawn_interval_seconds=SPAWN_INTERVAL_SECONDS,
)

print("Available proxies", len(manager.proxies.proxy_list))
print("Available window locations", len(manager.screen.spawn_locations))

GUI(manager).run()
