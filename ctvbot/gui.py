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

    def __init__(self, manager: InstanceManager):
        self.manager = manager
        self.queue_counter = 0
        self.root = tk.Tk()
        self.instances_boxes = []
        self._settings = Settings()

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

    def spawn_one_func(self):
        print("Spawning one instance. Please wait for alive & watching instances increase.")
        target_url = self.channel_url.get()
        threading.Thread(target=self.manager.spawn_instance, args=(target_url,)).start()

    def spawn_multi_func(self):
        print(f"Spawning {self.spawn_count.get()} instances. Please wait for alive & watching instances increase.")
        target_url = self.channel_url.get()
        spawn_count = int(self.spawn_count.get())
        threading.Thread(target=self.manager.spawn_instances, args=(spawn_count, target_url)).start()

    def spawn_auto_func(self, widget):
        if not self.manager.isAutoSpawning:
            target_url = self.channel_url.get()
            max_target = self._settings.General.getint("auto_spawn_target", fallback=16)
            threading.Thread(target=self.manager.begin_auto_spawn, args=(max_target, target_url)).start()
            widget.configure(text="Stop Auto")
        else:
            self.manager.end_auto_spawn()
            widget.configure(text="Spawn Auto")

    def delete_one_func(self):
        print("Destroying one instance. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_latest).start()

    def delete_all_func(self):
        print("Destroying all instances. Please wait for alive & watching instances decrease.")
        threading.Thread(target=self.manager.delete_all_instances).start()

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

    @staticmethod
    def validate_clamp(value, max, default):
        if value == -1:
            return default
        if value >= max:
            return max
        if value < 0:
            return 0
        return value

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

        root.title(f"Crude twitch viewer bot | v{version} | jlplenio")

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

        channel_url = tk.Entry(root, width=45, name="channel_url_entry", textvariable=self.channel_url)
        channel_url.place(x=left, y=10)
        #channel_url.insert(0, settings.General.get("channel_url", fallback="https://www.twitch.tv/channel_name"))

        spawn_one = tk.Button(
            root,
            width=10,
            anchor="w",
            text="Spawn 1",
            command=lambda: self.spawn_one_func(),
        )
        spawn_one.place(x=left, y=35)
        spawn_multi = tk.Button(
            root,
            width=10,
            anchor="w",
            text=f"Spawn {str(self.spawn_count.get())}",
            command=lambda: self.spawn_multi_func(),
        )
        spawn_multi.place(x=left, y=65)
        spawn_auto = tk.Button(
            root,
            width=10,
            anchor="w",
            text=f"Spawn Auto",
            command=lambda: self.spawn_auto_func(spawn_auto),
        )
        spawn_auto.place(x=left+100, y=35)
        destroy_one = tk.Button(
            root,
            width=10,
            anchor="w",
            text="Destroy last",
            command=lambda: self.delete_one_func(),
        )
        destroy_one.place(x=left+200, y=35)
        destroy_all = tk.Button(
            root,
            width=10,
            anchor="w",
            text="Destroy all",
            command=lambda: self.delete_all_func(),
        )
        destroy_all.place(x=left+200, y=65)
        
        spawn_count = tk.Entry(
            root, 
            width=5,
            name="spawn_count_entry", 
            textvariable=self.spawn_count
        )

        def validate_spawn_count(P):
            input = str(P)

            if (len(input) == 0): # empty string
                return True
            elif (not str.isdigit(input)): # invalid string with non-digits
                return False
        
            spawn_multi.configure(text=f"Spawn {input}")
            return True

        validate_spawn_count_handle = root.register(validate_spawn_count)
        spawn_count.configure(validate="key", validatecommand=(validate_spawn_count_handle, "%P"))
        spawn_count.place(x=left, y=94)
        
        spawn_auto_max = tk.Entry(
            root, 
            width=5,
            name="spawn_auto_max_entry", 
            textvariable=self.spawn_auto_max
        )

        def validate_spawn_auto_max(P):
            input = str(P)

            if (len(input) == 0): # empty string
                return True
            elif (not str.isdigit(input)): # invalid string with non-digits
                return False
        
            return True

        validate_spawn_auto_max_handle = root.register(validate_spawn_auto_max)
        spawn_auto_max.configure(validate="key", validatecommand=(validate_spawn_auto_max, "%P"))
        spawn_auto_max.place(x=left+100, y=65)

        headless_checkbox = ttk.Checkbutton(
            root,
            text="headless",
            variable=self.headless,
            command=lambda: self.manager.set_headless(self.headless.get()),
            onvalue=True,
            offvalue=False,
        )
        headless_checkbox.place(x=left+100, y=94)

        auto_restart_checkbox = ttk.Checkbutton(
            root,
            variable=self.auto_restart,
            text="auto restart",
            command=lambda: self.manager.set_auto_restart(self.auto_restart.get()),
            onvalue=True,
            offvalue=False,
        )
        auto_restart_checkbox.place(x=left+200, y=94)

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
            proxy_available.configure(text=len(self.manager.proxies.proxy_list))
            alive_instances.configure(text=self.manager.instances_alive_count)
            watching_instances.configure(text=str(self.manager.instances_watching_count))

            # Resource usage
            cpu_usage_text.configure(text=" {:.2f}% CPU".format(psutil.cpu_percent()))
            ram_usage_text.configure(text=" {:.2f}% RAM".format(psutil.virtual_memory().percent))

            root.after(750, refresher)

        refresher()

        # redirect stdout
        def redirector(str_input):
            if self.root and self._alive:
                text_area.configure(state="normal")
                text_area.insert(tk.END, str_input)
                text_area.see(tk.END)
                text_area.configure(state="disabled")
            else:
                sys.stdout = sys.__stdout__

        sys.stdout.write = redirector

        def onDestroy(evt):
            if evt.widget is root:
                self._alive = False
                self.manager.end_auto_spawn()
                self.save_settings()

        root.resizable(False, False)
        root.bind("<Destroy>", onDestroy)
        root.mainloop()