# -*- coding: utf-8 -*-

"""
===========================================
  page_erase_folder.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  Clayton Bradley - Feb 2019
===========================================
"""

from datetime import datetime
import os.path
import subprocess
import sys
from PIL import Image, ImageFont, ImageDraw
from .HAT_Utilities import get_device


try:
    import psutil
except ImportError:
    print("The psutil library was not found. "
          "Run 'sudo -H pip install psutil' to install it.")
    sys.exit()


class PageEraseFolder:
    def __init__(self, device):
        self.device = device

    def draw_page(self):
        # get an image
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/erase_folder.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageEraseFolder(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
