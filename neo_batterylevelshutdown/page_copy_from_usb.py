# -*- coding: utf-8 -*-

"""
===========================================
  page_copy_from_usb.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

import os.path
from PIL import Image
from .HAT_Utilities import get_device


class PageCopyFromUsb:
    def __init__(self, device):
        self.device = device


    def draw_page(self):
        # get an image
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/copy_from_usb.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)
        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageCopyFromUsb(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
