from ctvbot.gui import GUI
from ctvbot.manager import InstanceManager
from ctvbot.settings import Settings
from ctvbot.instance import Instance
from ctvbot.service import RestartChecker
from ctvbot.proxy import ProxyGetter

settings = Settings()

SPAWNER_THREAD_COUNT     = settings.General.getint("multi_spawn_count", fallback=3)
CLOSER_THREAD_COUNT      = settings.General.getint("closer_thread_count", fallback=10)
HEADLESS                 = settings.General.getboolean("headless", fallback=True)
AUTO_RESTART             = settings.General.getboolean("auto_restart", fallback=True)
SPAWN_INTERVAL_SECONDS   = settings.General.getint("spawn_interval_seconds", fallback=2)
RESTART_INTERVAL_SECONDS = settings.General.getint("restart_interval_seconds", fallback=1200)

PROXY_FILE_NAME          = settings.Proxies.get("proxy_path", fallback="proxy_list.txt")
PROXIES_ENABLED          = settings.Proxies.get("enabled", fallback="").splitlines(False)
PROXIES_DISABLED         = settings.Proxies.get("disabled", fallback="").splitlines(False)

BROWSER_TYPE = settings.Browsers.get("launch", fallback="chromium")
BROWSER_PATH = settings.Browsers.get(BROWSER_TYPE, fallback=None)

TIMEOUT_RETRY  = settings.Instance.getint("timeout.retry",  fallback=None)
TIMEOUT_RELOAD = settings.Instance.getint("timeout.reload", fallback=None)
TIMEOUT_WAIT   = settings.Instance.getint("timeout.wait",   fallback=None)

Instance.config_browser(BROWSER_TYPE, BROWSER_PATH)
Instance.configure(retrySeconds=TIMEOUT_RETRY, reloadSeconds=TIMEOUT_RELOAD, waitSeconds=TIMEOUT_WAIT,
                         getConfigValue=lambda key, fallback: settings.Instance.getint(key, fallback=fallback))

restart_checker = RestartChecker(RESTART_INTERVAL_SECONDS)
proxies = ProxyGetter(PROXY_FILE_NAME, sorted((dict.fromkeys(PROXIES_ENABLED, True) | dict.fromkeys(PROXIES_DISABLED, False)).items()))

manager = InstanceManager(
    spawn_thread_count=SPAWNER_THREAD_COUNT,
    delete_thread_count=CLOSER_THREAD_COUNT,
    headless=HEADLESS,
    auto_restart=AUTO_RESTART,
    proxies_or_proxy_file_name=proxies,
    spawn_interval_seconds=SPAWN_INTERVAL_SECONDS,
    restart_checker=restart_checker,
)

print("Available proxies", len(manager.proxies))
print("Available window locations", len(manager.screen.spawn_locations))

GUI(manager, settings).run()
