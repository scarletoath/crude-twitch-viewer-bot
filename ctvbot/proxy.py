import logging
import os
import random

logger = logging.getLogger(__name__)


class ProxyGetter:
    def __init__(self, proxy_file_name="proxy_list.txt"):
        self._proxy_list = []
        self._pathed_file_name = os.path.join(os.getcwd(), "proxy", proxy_file_name)
        self._build_proxy_list()

    def __len__(self):
        return len(self._proxy_list)

    def _build_proxy_list(self, clear=False):
        try:
            if self._pathed_file_name.endswith(".json"):
                raise NotImplementedError("JSON file not implemented yet")
            elif self._pathed_file_name.endswith(".txt"):
                if clear:
                    self._proxy_list.clear()
                self._build_proxy_list_txt()
            else:
                print("File type not supported")
        except Exception as e:
            logger.exception(e)
            raise FileNotFoundError(f"Unable to find {self.pathed_file_name}")

    def _build_proxy_list_txt(self):
        with open(self._pathed_file_name, "r") as fp:
            proxy_list = fp.read().splitlines()

        for proxy in proxy_list:
            proxy_parts = proxy.split(":")
            num_parts = len(proxy_parts)

            if num_parts >= 2:
                username = proxy_parts[2] if num_parts >= 3 else ''
                password = proxy_parts[3] if num_parts >= 4 else ''
                ip_port = ":".join(proxy_parts[0:2])

                if username != "username":
                    self._proxy_list.append(
                        {
                            "server": "http://" + ip_port,
                            "username": username,
                            "password": password,
                        }
                    )

        random.shuffle(self._proxy_list)

    def refresh(self):
        num_before = len(self)
        self._build_proxy_list(True)
        num_after = len(self)

        msg = f"Refreshed proxies: Was {num_before}, Now {num_after}"
        logger.info(msg)
        logger.guiOnly(msg)

    def get_proxy_as_dict(self) -> dict:
        if not self._proxy_list:
            return {}

        proxy = self._proxy_list.pop(0)
        self._proxy_list.append(proxy)
        return proxy
