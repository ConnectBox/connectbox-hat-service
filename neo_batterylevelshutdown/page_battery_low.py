# -*- coding: utf-8 -*-

"""
===========================================
  page_battery_low.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

import os.path
from PIL import Image
from neo_batterylevelshutdown.HAT_Utilities import get_device


class PageBatteryLow:
    def __init__(self, device):
        self.device = device

    def draw_page(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))

        img_path = dir_path + '/assets/battery_low.png'

        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageBatteryLow(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
