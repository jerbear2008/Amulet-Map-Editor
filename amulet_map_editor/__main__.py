#!/usr/bin/env python3

import sys

if sys.version_info[:2] < (3, 7):
    raise Exception("Must be using Python 3.7+")

import os
import traceback
import wx.__version__
from amulet_map_editor import log
from amulet_map_editor.api.framework import AmuletApp


if __name__ == "__main__":
    if sys.platform == "linux" and wx.__version__.VERSION >= (4, 1, 1):
        # bug 247
        os.environ["PYOPENGL_PLATFORM"] = "egl"
    try:
        app = AmuletApp(0)
        app.MainLoop()
    except Exception as e:
        log.critical(
            f"Amulet Crashed. Sorry about that. Please report it to a developer if you think this is an issue. \n{traceback.format_exc()}"
        )
        input("Press ENTER to continue.")
