# -*- coding: utf-8 -*-

"""
===========================================
  page_none.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

from neo_batterylevelshutdown.HAT_Utilities import get_device


class PageBlank:
    def __init__(self, device):
        self.device = device

    def draw_page(self):
        # turn off the OLED
        self.device.hide()


if __name__ == "__main__":
    try:
        PageBlank(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
