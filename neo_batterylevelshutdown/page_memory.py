# -*- coding: utf-8 -*-

"""
===========================================
  page_memory.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

import sys
import os.path
from PIL import Image, ImageFont, ImageDraw

from .HAT_Utilities import get_device
import neo_batterylevelshutdown.globals as globals


try:
    import psutil
except ImportError:
    print("The psutil library was not found. "
          "Run 'sudo -H pip install psutil' to install it.")
    sys.exit()


class PageMemory:
    def __init__(self, device):
        self.device = device

    @staticmethod
    def bytes2human(n):
        """
        >>> bytes2human(10000)
        '9K'
        >>> bytes2human(100001221)
        '95M'
        """
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10
        for s in reversed(symbols):
            if n >= prefix[s]:
                x = (float(n) / prefix[s])
                value = str("{:3.1f}".format(x))
                return '%s%s' % (value, s)
        return "%sB" % n

    @staticmethod
    def mem_usage():
        return psutil.virtual_memory()

    @staticmethod
    def disk_usage(dir_name):
        return psutil.disk_usage(dir_name)

    @staticmethod
    def cpu_usage():
        return psutil.cpu_percent(interval=0)

    @staticmethod
    def network(iface):
        return psutil.net_io_counters(pernic=True)[iface]

    def draw_page(self):
        # get an image
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/memory_page.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/connectbox.ttf'
        font20 = ImageFont.truetype(font_path, globals.font20)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        # cpu usage
        d.text((50, 1), "%.0f%%" % PageMemory.cpu_usage(),
               font=font20, fill="black")

        # memory usage
        usage = PageMemory.mem_usage()
        d.text((50, 21), "%.0f%%" %
               (100 - usage.percent), font=font20, fill="black")
        d.text((85, 21), "%s" % PageMemory.bytes2human(usage.available),
               font=font20, fill="black")

        # disk usage
        usage = PageMemory.disk_usage('/media/usb0')
        d.text((50, 42), "%.0f%%" % usage.percent, font=font20, fill="black")
        d.text((85, 42), "%s" % PageMemory.bytes2human(usage.total),
               font=font20, fill="black")

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageMemory(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
