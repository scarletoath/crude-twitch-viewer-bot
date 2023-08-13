from __future__ import annotations

import logging
import os
import queue

import psutil

from logging.handlers import *

class _FuncHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level=level)

        self._funcs = set()

    def emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
            for func in self._funcs:
                func(msg)
        except(e):
            self.handleError(record)

    def addFunc(self, func:function):
        self._funcs.add(func)

    def removeFunc(self, func:function):
        self._funcs.remove(func)

def setup():
    import sys

    print(sys.argv[0])

    def logGuiOnly(self:logging.Logger, msg:string):
        self.log(logging.GUI_ONLY, msg)

    def registerFuncHandler(func:function, isAdd:bool = True):
        if isAdd:
            queueConsumer.addFunc(func)
        else:
            queueConsumer.removeFunc(func)

    logging.GUI_ONLY = logging.INFO + 5
    logging.addLevelName(logging.GUI_ONLY, "GUI_ONLY")
    logging.Logger.guiOnly = logGuiOnly
    logging.Logger.registerFuncHandler = registerFuncHandler

    gui_queue = queue.Queue()
    queueHandler = QueueHandler(gui_queue)
    queueHandler.setLevel(logging.GUI_ONLY)
    queueHandler.addFilter(lambda record:record.levelno == logging.GUI_ONLY)
    queueHandler.setFormatter(logging.Formatter("%(message)s\n"))

    queueConsumer = _FuncHandler()
    queueListener = QueueListener(gui_queue, queueConsumer)

    fileHandler = logging.FileHandler("ctvbot.log", mode="w")
    fileHandler.addFilter(lambda record:record.levelno != logging.GUI_ONLY)

    handlers = [
        fileHandler,
        queueHandler,
    ]

    if os.getenv("DEBUG"):
        print("DEBUG ON")
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s;%(levelname)s;%(HWUsage)s;%(threadName)s;%(module)s;%(funcName)s;%(message)s",
        handlers=handlers,
    )

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.HWUsage = f"{psutil.cpu_percent(interval=None):.0f}_{psutil.virtual_memory().percent:.0f}"
        return record

    logging.setLogRecordFactory(record_factory)
    queueListener.start()