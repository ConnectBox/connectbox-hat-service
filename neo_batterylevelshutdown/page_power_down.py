# -*- coding: utf-8 -*-

"""
===========================================
  page_power_down.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  DorJamJr - Sept 2021
===========================================
"""

import os.path
from PIL import Image
from .HAT_Utilities import get_device


class PagePowerDown:
    def __init__(self, device):
        self.device = device

    def draw_page(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))

        img_path = dir_path + '/assets/on_off.png'

        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PagePowerDown(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
