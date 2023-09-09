import logging
import os
import random

logger = logging.getLogger(__name__)

_DEFAULT_FOLDER = "proxy"
_DEFAULT_FILE   = "proxy_list.txt"
_DEFAULT_EXT    = ".txt"
_IGNORE_FILES   = ["user-agents.txt"]

class ProxyGetter:

    def __init__(self, proxy_file_name=_DEFAULT_FILE, initial_state={}):
        self._proxy_list = []
        self._is_dir = False
        self._pathed_file_name = None
        self._sources = dict(initial_state) # Empty if nothing specified, or fill with given data

        self._validate_and_set_path(proxy_file_name)
        self._build_proxy_list()

    def __len__(self):
        return len(self._proxy_list)

    @property
    def source_paths(self):
        """Returns source paths found. Note this excludes the folder."""
        return self._sources.keys()

    def is_source_enabled(self, path):
        return self._sources.get(path, False)

    def enable_source_path(self, path, is_enabled=True):
        if path in self._sources:
            self._sources[path] = is_enabled

    def _validate_and_set_path(self, path):
        # Try raw absolute path > joined abs path > joined abs path with default proxy folder
        candidate_paths = []
        if os.path.isabs(path):
            candidate_paths.insert(0, path)
        else:
            candidate_paths.append(os.path.join(os.getcwd(), path))
            candidate_paths.append(os.path.join(os.getcwd(), _DEFAULT_FOLDER, path))

        for candidate_path in candidate_paths:
            if os.path.lexists(candidate_path):
                if os.path.isdir(candidate_path):
                   self._is_dir = True
                self._pathed_file_name = candidate_path
                return

    def _build_proxy_list(self, clear=False):
        if not self._pathed_file_name:
            return

        # Get all files in dir if dir path
        all_paths = [self._pathed_file_name] if not self._is_dir else list(map(lambda path: os.path.join(self._pathed_file_name, path), os.listdir(self._pathed_file_name)))
        has_default_file = _DEFAULT_FILE in [os.path.basename(path) for path in all_paths]

        # Append all valid proxies from all found files
        for path in all_paths:
            try:
                base_path = os.path.basename(path)
                path_ext  = os.path.splitext(base_path)[1]
                
                if base_path in _IGNORE_FILES:
                    continue

                if path_ext == ".json":
                    raise NotImplementedError(f"JSON file not implemented yet : {path}")
                elif path_ext == ".txt":
                    # Check if toggled, or default to enabled
                    is_default_file = base_path == _DEFAULT_FILE
                    enabled = self._sources.setdefault(base_path, (not has_default_file) or is_default_file)

                    if not enabled:
                        continue

                    if clear:
                        self._proxy_list.clear()
                        clear = False # Only clear the first time
                    self._build_proxy_list_txt(path)
                else:
                    print(f"File type {path_info.ext} not supported : {path}")
            except Exception as e:
                logger.exception(e)
                raise FileNotFoundError(f"Unable to find {path}")

        random.shuffle(self._proxy_list)

    def _build_proxy_list_txt(self, path):
        with open(path, "r") as fp:
            proxy_list = fp.read().splitlines()

        add_count = 0
        for proxy in proxy_list:
            proxy_parts = proxy.split(":")
            num_parts = len(proxy_parts)

            if num_parts >= 2:
                # Optional username/password sections
                username = proxy_parts[2] if num_parts >= 3 else ''
                password = proxy_parts[3] if num_parts >= 4 else ''
                ip_port = ":".join(proxy_parts[0:2])

                if username != "username":
                    add_count += 1
                    self._proxy_list.append(
                        {
                            "server": "http://" + ip_port,
                            "username": username,
                            "password": password,
                        }
                    )

        if add_count > 0:
            logger.info(f"Added {add_count} proxies from {path}")


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
