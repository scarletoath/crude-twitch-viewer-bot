import datetime
import logging
import os
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import psutil
import toml

from . import utils
from .manager import InstanceManager
from .utils import InstanceCommands
from .settings import Settings

logger = logging.getLogger(__name__)

system_default_color = None


class InstanceBox(tk.Frame):
    _color_codes = {
        "inactive": system_default_color,
        "starting": "grey",
        "initialized": "yellow",
        "restarting": "#ff7f00",
        "buffering": "#00aaaa",
        "watching": "#44d209",
        "shutdown": system_default_color,
    }

    @staticmethod
    def SetDefaultColor(color):
        InstanceBox._color_codes["inactive"] = InstanceBox._color_codes["shutdown"] = color

    def __init__(self, manager, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.instance_id = None
        self.manager = manager

        self.bind(
            "<Button-1>", lambda event: self.manager.queue_command(self.instance_id, InstanceCommands.REFRESH)
        )  # left click
        self.bind(
            "<Button-3>", lambda event: self.manager.queue_command(self.instance_id, InstanceCommands.EXIT)
        )  # right click
        self.bind(
            "<Control-1>", lambda event: self.manager.queue_command(self.instance_id, InstanceCommands.SCREENSHOT)
        )  # control left click

    def modify(self, status, instance_id):
        self.instance_id = instance_id

        color = InstanceBox._color_codes[status.value]
        self.configure(background=color)


class GUI:
    _DEFAULT_WIDTH = 600
    _DEFAULT_HEIGHT = 305
    _DEFAULT_TOP = 500
    _DEFAULT_LEFT = 500

    _log_lock = threading.Lock()

    def __init__(self, manager: InstanceManager, settings: Settings = None):
        self.manager = manager
        self.queue_counter = 0
        self.root = tk.Tk()
        self.instances_boxes = []
        self._settings = settings if settings is not None else Settings()

        self.headless = tk.BooleanVar(value=manager.get_headless())
        self.auto_restart = tk.BooleanVar(value=manager.get_auto_restart())
        self.spawn_count = tk.StringVar(value=str(self._settings.General.getint("multi_spawn_count", fallback=3)))
        self.spawn_auto_max = tk.StringVar(value=str(self._settings.General.getint("auto_spawn_target", fallback=16)))
        self.channel_url = tk.StringVar(value=self._settings.General.get("channel_url", fallback="https://www.twitch.tv/channel_name"))

        global system_default_color
        system_default_color = self.root.cget("bg")
        InstanceBox.SetDefaultColor(system_default_color)

    def __del__(self):
        print("Gui shutting down", datetime.datetime.now())

    ### Helpers ###

    def spawn_one_func(self):
        logger.guiOnly("Spawning one instance. Please wait for alive & watching instances increase.")
        target_url = self.channel_url.get()
        threading.Thread(target=self.manager.spawn_instance, args=(target_url,)).start()

    def spawn_multi_func(self):
        logger.guiOnly(f"Spawning {self.spawn_count.get()} instances. Please wait for alive & watching instances increase.")
        target_url = self.channel_url.get()
        spawn_count = int(self.spawn_count.get())
        threading.Thread(target=self.manager.spawn_instances, args=(spawn_count, target_url)).start()

    def spawn_auto_func(self, widget):
        if not self.manager.isAutoSpawning:
            target_url = self.channel_url.get()
            max_target = int(self.spawn_auto_max.get())
            threading.Thread(target=self.manager.begin_auto_spawn, args=(max_target, target_url)).start()
            widget.configure(text="Stop")
        else:
            self.manager.end_auto_spawn()
            widget.configure(text="Auto")

    def delete_one_func(self):
        logger.guiOnly("Destroying latest instance. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_latest).start()

    def delete_all_func(self):
        logger.guiOnly(f"Destroying all {self.manager.count} instances. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_all_instances).start()

    def restart_all_func(self):
        logger.guiOnly(f"Restarting all {self.manager.count} instances. Please wait for alive & watching instances change.")
        threading.Thread(target=self.manager.restart_all_instances, args=(True,)).start()

    def save_settings(self):
        logger.info("Saving settings to file.")
        
        settings = self._settings
        settings.General["multi_spawn_count"] = self.spawn_count.get()
        settings.General["auto_spawn_target"] = self.spawn_auto_max.get()
        settings.General["headless"] = str(self.headless.get())
        settings.General["auto_restart"] = str(self.auto_restart.get())
        settings.General["channel_url"] = self.channel_url.get()

        settings.Window["top"] = str(self.root.winfo_y())
        settings.Window["left"] = str(self.root.winfo_x())

        settings.save_settings()

    ### Validators ###

    @staticmethod
    def validate_clamp(value, max, default):
        if value == -1:
            return default
        if value >= max:
            return max
        if value < 0:
            return 0
        return value

    @staticmethod
    def create_numeric_validator(callback=None):
        def validator(P):
            input = str(P)

            if (len(input) == 0): # empty string
                return True
            elif (not str.isdigit(input)): # invalid string with non-digits
                return False
        
            if callback is not None:
                callback(input)
            return True
        return validator

    ### Main setup and loop ###

    def run(self):
        root = self.root
        self._alive = True

        settings = self._settings

        # Get window position from settings, and clamp to visible window
        win_x = GUI.validate_clamp(settings.Window.getint("left", fallback=GUI._DEFAULT_LEFT), root.winfo_screenwidth() - GUI._DEFAULT_WIDTH, GUI._DEFAULT_LEFT)
        win_y = GUI.validate_clamp(settings.Window.getint("top", fallback=GUI._DEFAULT_TOP), root.winfo_screenheight() - GUI._DEFAULT_HEIGHT, GUI._DEFAULT_TOP)
        root.geometry(f"{GUI._DEFAULT_WIDTH}x{GUI._DEFAULT_HEIGHT}+{win_x}+{win_y}")

        # path to use, when the tool is not package with pyinstaller -onefile
        non_pyinstaller_path = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

        # Pyinstaller fix to find added binaries in extracted project folder in TEMP
        path_to_binaries = getattr(sys, "_MEIPASS", non_pyinstaller_path)  # default to last arg
        path_to_icon = os.path.abspath(os.path.join(path_to_binaries, "ctvbot_logo.ico"))

        if os.name == "nt":
            root.iconbitmap(path_to_icon)

        path_to_toml = os.path.abspath(os.path.join(path_to_binaries, "pyproject.toml"))
        version = toml.load(path_to_toml)["tool"]["poetry"]["version"]

        root.title(f"Crude twitch viewer bot | v{version} | jlplenio (modified by scarletoath)")

        # separators
        separator_left = ttk.Separator(orient="vertical")
        separator_left.place(x=125, relx=0, rely=0, relwidth=0.2, relheight=0.5)
        separator_right = ttk.Separator(orient="vertical")
        separator_right.place(x=-170, relx=1, rely=0, relwidth=0.2, relheight=0.5)

        # left
        left = 20

        proxy_available_text = tk.Label(root, text="Proxies Available", borderwidth=2)
        proxy_available_text.place(x=left, y=10)
        proxy_available = tk.Label(root, text="0", borderwidth=2, relief="solid", width=5)
        proxy_available.place(x=left+30, y=40)

        lbl_buy = tk.Label(root, text="(buy more)", fg="blue", cursor="hand2")
        lbl_buy.bind(
            "<Button-1>",
            lambda event: webbrowser.open("https://www.webshare.io/?referral_code=w6nfvip4qp3g"),
        )
        lbl_buy.place(x=left+18, y=62)
        tk.Button(
            root,
            width=7,
            anchor=tk.CENTER,
            text="Refresh",
            command=self.manager.refresh_proxies,
        ).place(x=left+20, y=87.5)

        # right
        left = 440

        instances_text = tk.Label(root, text="Instances", borderwidth=2)
        instances_text.place(x=left+15, y=10)

        alive_instances_text = tk.Label(root, text="alive", borderwidth=2)
        alive_instances_text.place(x=left+15, y=40)
        watching_instances_text = tk.Label(root, text="watching", borderwidth=2)
        watching_instances_text.place(x=left+15, y=60)

        alive_instances = tk.Label(root, text=0, borderwidth=2, relief="solid", width=5)
        alive_instances.place(x=left+90, y=40)
        watching_instances = tk.Label(root, text=0, borderwidth=2, relief="solid", width=5)
        watching_instances.place(x=left+90, y=60)

        cpu_usage_text = tk.Label(root, text="CPU", borderwidth=2)
        cpu_usage_text.place(x=left, y=88)
        ram_usage_text = tk.Label(root, text="RAM", borderwidth=2)
        ram_usage_text.place(x=left+70, y=88)

        # mid log
        left = 140
        button_width=3
        entry_width=4
        text_anchor=tk.CENTER

        midFrame = ttk.Frame(root, width=304, height=120, padding=(10, 10), relief="flat")
        midFrame.grid_propagate(0)
        midFrame.place(x=126, y=0)

        channel_url = tk.Entry(midFrame, width=20, name="channel_url_entry", textvariable=self.channel_url)
        channel_url.grid(row=0, column=0, columnspan=6, sticky=tk.EW)

        # - Spawn
        tk.Label(midFrame, text="Spawn").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        spawn_one = tk.Button(
            midFrame,
            width=button_width,
            anchor=text_anchor,
            text="1",
            command=lambda: self.spawn_one_func(),
        )
        spawn_one.grid(row=1, column=1, sticky=tk.EW)
        spawn_multi = tk.Button(
            midFrame,
            width=button_width,
            anchor=text_anchor,
            text=f"{str(self.spawn_count.get())}",
            command=lambda: self.spawn_multi_func(),
        )
        spawn_multi.grid(row=1, column=2, sticky=tk.EW)
        spawn_count = tk.Entry(
            midFrame, 
            width=entry_width,
            name="spawn_count_entry", 
            textvariable=self.spawn_count,
            validate="key",
            validatecommand=(root.register(GUI.create_numeric_validator(lambda input: spawn_multi.configure(text=f"{input}"))), "%P"),
        )
        spawn_count.grid(row=1, column=3, padx=(0, 10))
        spawn_auto = tk.Button(
            midFrame,
            width=button_width,
            anchor=text_anchor,
            text=f"Auto",
            command=lambda: self.spawn_auto_func(spawn_auto),
        )
        spawn_auto.grid(row=1, column=4, sticky=tk.EW)
        spawn_auto_max = tk.Entry(
            midFrame, 
            width=entry_width,
            name="spawn_auto_max_entry", 
            textvariable=self.spawn_auto_max,
            validate="key",
            validatecommand=(root.register(GUI.create_numeric_validator()), "%P"),
        )
        spawn_auto_max.grid(row=1, column=5)

        # - Destroy
        tk.Label(midFrame, text="Destroy", anchor=tk.W, padx=0).grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        destroy_one = tk.Button(
            midFrame,
            width=button_width,
            anchor=text_anchor,
            text="Last",
            command=lambda: self.delete_one_func(),
        )
        destroy_one.grid(row=2, column=1, sticky=tk.EW)
        destroy_all = tk.Button(
            midFrame,
            width=button_width,
            anchor=text_anchor,
            text="All",
            command=lambda: self.delete_all_func(),
        )
        destroy_all.grid(row=2, column=2, sticky=tk.EW)

        # - Restart
        tk.Label(midFrame, text="Restart", anchor=tk.W, padx=0).grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        restart_all = tk.Button(
            midFrame,
            width=button_width,
            anchor=text_anchor,
            text="All",
            command=lambda: self.restart_all_func(),
        )
        restart_all.grid(row=3, column=1, sticky=tk.EW)
        auto_restart_checkbox = ttk.Checkbutton(
            midFrame,
            variable=self.auto_restart,
            text="Auto",
            command=lambda: self.manager.set_auto_restart(self.auto_restart.get()),
            onvalue=True,
            offvalue=False,
        )
        auto_restart_checkbox.grid(row=3, column=1, columnspan=2, sticky=tk.E)
        
        # - Misc
        headless_checkbox = ttk.Checkbutton(
            midFrame,
            text="headless",
            variable=self.headless,
            command=lambda: self.manager.set_headless(self.headless.get()),
            onvalue=True,
            offvalue=False,
        )
        headless_checkbox.grid(row=3, column=3, columnspan=3, sticky=tk.E)

        # // Post grid config
        col_count, row_count = midFrame.grid_size()
        col_weights = [None, 1, 1, None, 1, None]
        for col in range(col_count):
            midFrame.columnconfigure(col, pad=4, weight=col_weights[col])
        for row in range(row_count):
            midFrame.rowconfigure(row, pad=2)

        # mid text box
        text_area = ScrolledText(root, height="7", width="92", font=("regular", 8))
        text_area.place(
            x=20,
            y=120,
        )

        for row in range(5):
            for col in range(50):
                box = InstanceBox(
                    self.manager,
                    self.root,
                    bd=0.5,
                    relief="raised",
                    width=10,
                    height=10,
                )
                box.place(x=24 + col * 11, y=230 + row * 12)
                self.instances_boxes.append(box)

        # bottom
        lbl = tk.Label(
            root,
            text=r"https://github.com/jlplenio/crude-twitch-viewer-bot",
            fg="blue",
            cursor="hand2",
        )
        lbl.bind("<Button-1>", lambda event: webbrowser.open(lbl.cget("text")))
        lbl.place(x=150, y=288)

        # refresh counters
        def refresher():
            instances_overview = self.manager.instances_overview

            # Update anything that isn't inactive
            for (id, status), box in zip(instances_overview.items(), self.instances_boxes):
                box.modify(status, id)

            # Reset newly inactive instance boxes
            for index in range(len(instances_overview), len(self.instances_boxes)):
                self.instances_boxes[index].modify(utils.InstanceStatus.INACTIVE, None)

            # Instances counts
            proxy_available.configure(text=len(self.manager.proxies))
            alive_instances.configure(text=self.manager.instances_alive_count)
            watching_instances.configure(text=str(self.manager.instances_watching_count))

            # Resource usage
            cpu_usage_text.configure(text=" {:.2f}% CPU".format(psutil.cpu_percent()))
            ram_usage_text.configure(text=" {:.2f}% RAM".format(psutil.virtual_memory().percent))

            root.after(250, refresher)

        refresher()

        # redirect stdout
        def redirector(str_input):
            if self.root and self._alive:
                with GUI._log_lock: # Ensures log writes don't overlap, which can result in mixed up lines
                    text_area.configure(state=tk.NORMAL)
                    text_area.insert(tk.END, str_input)
                    text_area.see(tk.END)
                    text_area.configure(state=tk.DISABLED)
            else:
                print(str_input, flush=True)

        logging.Logger.registerFuncHandler(redirector)

        def onDestroy(evt):
            if evt.widget is root:
                self._alive = False
                self.manager.end_auto_spawn()
                self.save_settings()

        root.resizable(False, False)
        root.bind("<Destroy>", onDestroy)
        root.mainloop()