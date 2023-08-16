import datetime
import json
import logging
import time

from dateutil.relativedelta import relativedelta

from ctvbot import utils
from ctvbot.instance import Instance

logger = logging.getLogger(__name__)


class Unknown(Instance):
    name = "UNKNOWN"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def todo_every_loop(self):
        self.page.keyboard.press("Tab")

    def update_status(self):
        pass

    def todo_after_spawn(self):
        self.goto_with_retry(self.target_url)
        self.page.wait_for_timeout(1000)


class Youtube(Instance):
    name = "YOUTUBE"
    cookie_css = ".eom-button-row.style-scope.ytd-consent-bump-v2-lightbox > ytd-button-renderer:nth-child(1) button"

    now_timestamp_ms = int(time.time() * 1000)
    next_year_timestamp_ms = int((datetime.datetime.now() + relativedelta(years=1)).timestamp() * 1000)
    local_storage = {
        "yt-player-quality": r"""{{"data":"{{\\"quality\\":144,\\"previousQuality\\":144}}","expiration":{0},"creation":{1}}}""".format(
            next_year_timestamp_ms, now_timestamp_ms
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def todo_every_loop(self):
        self.page.keyboard.press("Tab")

        try:
            self.page.click("button.ytp-ad-skip-button", timeout=100)
        except:
            pass

    def update_status(self):
        current_time = datetime.datetime.now()

        if not self.status_info:
            self.status_info = {
                "last_active_resume_time": 0,
                "last_active_timestamp": current_time - datetime.timedelta(seconds=10),
                "last_stream_id": None,
            }

        # If the stream was active less than 10 seconds ago, it's still being watched
        time_since_last_activity = current_time - self.status_info["last_active_timestamp"]
        if time_since_last_activity < datetime.timedelta(seconds=15):
            self.status = utils.InstanceStatus.WATCHING
            return

        # Fetch the current resume time for the stream
        current_resume_time = int(
            self.page.evaluate(
                '''() => {
            const element = document.querySelector(".ytp-progress-bar");
            return element.getAttribute("aria-valuenow");
        }'''
            )
        )

        if current_resume_time:
            # If the current resume time has advanced past the last active resume time, update and set status to
            if current_resume_time > self.status_info["last_active_resume_time"]:
                self.status_info["last_active_timestamp"] = current_time
                self.status_info["last_active_resume_time"] = current_resume_time
                self.status = utils.InstanceStatus.WATCHING
                return

        # If none of the above conditions are met, the stream is buffering
        self.status = utils.InstanceStatus.BUFFERING

    def todo_after_spawn(self):
        self.goto_with_retry("https://www.youtube.com/")

        self.page.wait_for_timeout(1000)

        try:
            self.page.click(self.cookie_css, timeout=10000)
        except:
            logger.warning("Cookie consent banner not found/clicked.")

        for key, value in self.local_storage.items():
            tosend = """window.localStorage.setItem('{key}','{value}');""".format(key=key, value=value)
            self.page.evaluate(tosend)

        self.goto_with_retry(self.target_url)
        self.page.keyboard.press("t")
        self.status = utils.InstanceStatus.INITIALIZED


class Kick(Instance):
    name = "KICK"
    local_storage = {
        "agreed_to_mature_content": "true",
        "kick_cookie_accepted": "true",
        "kick_video_size": "160p",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def todo_every_loop(self):
        self.page.keyboard.press("Tab")

    def update_status(self):
        pass

    def todo_after_spawn(self):
        self.goto_with_retry("https://kick.com/auth/login")
        self.page.wait_for_timeout(5000)

        for key, value in self.local_storage.items():
            tosend = """window.localStorage.setItem('{key}','{value}');""".format(key=key, value=value)
            self.page.evaluate(tosend)

        self.goto_with_retry(self.target_url)
        self.page.wait_for_timeout(1000)
        if 'cloudflare' in self.page.content().lower():
            raise utils.CloudflareBlockException("Blocked by Cloudflare.")


class Twitch(Instance):
    name = "TWITCH"
    cookie_css = "button[data-a-target=consent-banner-accept]"
    local_storage = {
        "mature": "true",
        "video-muted": '{"default": "false"}',
        "volume": "0.5",
        "video-quality": '{"default": "160p30"}',
        "lowLatencyModeEnabled": "false",
    }

    _player_selector = ".persistent-player"

    # Timeouts in milliseconds
    _timeout_cookie         = 15000
    _timeout_playerReady    = 15000
    _timeout_playerReloaded = 30000
    _timeout_matureButton   = 3000

    @staticmethod
    def _configure(getConfigValue):
        Twitch._timeout_cookie         = getConfigValue("timeout.cookie",         15) * 1000
        Twitch._timeout_playerReady    = getConfigValue("timeout.playerReady",    15) * 1000
        Twitch._timeout_playerReloaded = getConfigValue("timeout.playerReloaded", 30) * 1000
        Twitch._timeout_matureButton   = getConfigValue("timeout.matureButton",    3) * 1000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def todo_after_load(self):
        self.page.wait_for_selector(Twitch._player_selector, timeout=Twitch._timeout_playerReloaded)
        self.page.wait_for_timeout(Instance._timeout_buffer)
        self.page.keyboard.press("Alt+t") # theater mode

    def update_status(self):
        current_time = datetime.datetime.now()
        if not self.status_info:
            self.status_info = {
                "last_active_resume_time": 0,
                "last_active_timestamp": current_time - datetime.timedelta(seconds=10),
                "last_stream_id": None,
            }

        # If the stream was active less than 10 seconds ago, it's still being watched
        time_since_last_activity = current_time - self.status_info["last_active_timestamp"]
        if time_since_last_activity < datetime.timedelta(seconds=10):
            self.status = utils.InstanceStatus.WATCHING
            return

        # Fetch the current resume time for the stream
        fetched_resume_times = self.page.evaluate("window.localStorage.getItem('livestreamResumeTimes');")
        if fetched_resume_times:
            resume_times_dict = json.loads(fetched_resume_times)
            current_stream_id = list(resume_times_dict.keys())[-1]
            current_resume_time = list(resume_times_dict.values())[-1]

            # If this is the first run, set the last stream id to current stream id
            if not self.status_info["last_stream_id"]:
                self.status_info["last_stream_id"] = current_stream_id

            # If the stream has restarted, reset last_active_resume_time
            if current_stream_id != self.status_info["last_stream_id"]:
                self.status_info["last_stream_id"] = current_stream_id
                self.status_info["last_active_resume_time"] = 0

            # If the current resume time has advanced past the last active resume time, update and set status to
            if current_resume_time > self.status_info["last_active_resume_time"]:
                self.status_info["last_active_timestamp"] = current_time
                self.status_info["last_active_resume_time"] = current_resume_time
                self.status = utils.InstanceStatus.WATCHING
                return

        # If none of the above conditions are met, the stream is buffering
        self.status = utils.InstanceStatus.BUFFERING

    def todo_after_spawn(self):
        self.goto_with_retry("https://www.twitch.tv/login")

        try:
            self.page.click(self.cookie_css, timeout=Twitch._timeout_cookie)
        except:
            logger.warning("Cookie consent banner not found/clicked.")

        for key, value in self.local_storage.items():
            tosend = """window.localStorage.setItem('{key}','{value}');""".format(key=key, value=value)
            self.page.evaluate(tosend)

        self.page.set_viewport_size(
            {
                "width": self.location_info["width"],
                "height": self.location_info["height"],
            }
        )

        self.goto_with_retry(self.target_url)
        self.page.wait_for_timeout(Instance._timeout_buffer)
        self.page.wait_for_selector(Twitch._player_selector, timeout=Twitch._timeout_playerReady)
        self.page.keyboard.press("Alt+t") # theater mode
        self.page.wait_for_timeout(Instance._timeout_buffer)

        try:
            self.page.click(
                "button[data-a-target=content-classification-gate-overlay-start-watching-button]", timeout=Twitch._timeout_matureButton
            )
        except:
            logger.info("Mature button not found/clicked.")

        self.status = utils.InstanceStatus.INITIALIZED
