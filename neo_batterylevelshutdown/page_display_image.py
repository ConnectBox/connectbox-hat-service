# -*- coding: utf-8 -*-

"""
===========================================
  page_display_image.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  Clayton Bradley - Feb 2019
===========================================
"""

import os.path
import logging
from PIL import Image
from .HAT_Utilities import get_device


class PageDisplayImage:
    def __init__(self, device, imageName='error.png'):
        self.device = device
        self.imageName = imageName

    def draw_page(self):
        # display a specified impage
        logging.debug("Showing %s", self.imageName)
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/' + self.imageName
        if not os.path.isfile(img_path):
            img_path = dir_path + '/assets/error.png'

        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageDisplayImage(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
