import time


def test_open_one_instance(record_property):
    from ctvbot.manager import InstanceManager
    import urllib.request, re

    # get username of random online stream
    for i in range(10):
        html_text = urllib.request.urlopen("https://m.twitch.tv").read()
        if html_text:
            break
        time.sleep(1)
    username = re.search('"login":"*(.*?)"', str(html_text))[1]

    SPAWNER_THREAD_COUNT = 3
    CLOSER_THREAD_COUNT = 10
    PROXY_FILE_NAME = "proxy_list.txt"
    HEADLESS = True
    AUTO_RESTART = True
    SPAWN_INTERVAL_SECONDS = 2

    target_url = "https://www.twitch.tv/" + username
    print("Watching", str(target_url))

    restart_checker = RestartChecker(2)
    proxies = ProxyGetter(PROXY_FILE_NAME)

    manager = InstanceManager(
        spawn_thread_count=SPAWNER_THREAD_COUNT,
        delete_thread_count=CLOSER_THREAD_COUNT,
        headless=HEADLESS,
        auto_restart=AUTO_RESTART,
        proxies_or_proxy_file_name=proxies,
        spawn_interval_seconds=SPAWN_INTERVAL_SECONDS,
        target_url=target_url,
        restart_checker=restart_checker,
    )

    manager.spawn_instance()

    instance_is_watching = False
    for _ in range(60):
        if manager.instances_watching_count > 0:
            instance_is_watching = True
            break
        time.sleep(1)

    manager.__del__()

    assert instance_is_watching
