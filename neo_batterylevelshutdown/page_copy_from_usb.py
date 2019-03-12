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
import sys
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

        # # make a blank image for the text, initialized as transparent
        # txt = Image.new('RGBA', base.size, (255, 255, 255, 0))
        #
        # # get a font
        # font_path = dir_path + '/assets/connectbox.ttf'
        # font20 = ImageFont.truetype(font_path, 26)
        # font18 = ImageFont.truetype(font_path, 18)
        # # get a drawing context
        # d = ImageDraw.Draw(txt)
        #
        # # uptime
        # d.text((50, 0), PageInfo.uptime(), font=font18, fill="black")
        #
        # # connected users
        # d.text((20, 30), PageInfo.get_connected_users(),
        #        font=font20, fill="black")
        #
        # # network stats
        # try:
        #     stat = PageInfo.network('wlan0')
        #     d.text((58, 35), "Tx: %s" % PageInfo.bytes2human(
        #         stat.bytes_sent), font=font18, fill="black")
        #     d.text((58, 47), "Rx: %s" % PageInfo.bytes2human(
        #         stat.bytes_recv), font=font18, fill="black")
        # except KeyError:
        #     # no wifi enabled/available
        #     pass

        # out = Image.alpha_composite(img, txt)
        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageCopyFromUsb(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
