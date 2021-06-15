# -*- coding: utf-8 -*-

"""
===========================================
  page_info.py
  https://github.com/kirkdwilson/MV-WayPoint/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
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


class PageInfo:
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
                value = int(float(n) / prefix[s])
                return '%s%s' % (value, s)
        return "%sB" % n

    @staticmethod
    def uptime():
        # uptime
        uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
        if uptime.days > 0:
            # Only show days
            duration_str = "%s days" % (uptime.days,)
        else:
            # Drop microseconds
            duration_str = str(uptime).split('.')[0]

        return "Up: %s" % (duration_str,)

    @staticmethod
    def get_connected_users():
        c = subprocess.run(['iw', 'dev', 'wlan0', 'station',
                            'dump'], stdout=subprocess.PIPE)
        connected_user_count = len([line for line in c.stdout.decode(
            "utf-8").split('\n') if line.startswith("Station")])
        return "%s" % connected_user_count

    @staticmethod
    def network(iface):
        return psutil.net_io_counters(pernic=True)[iface]

    def draw_page(self):
        # get an image
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/info_page.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/connectbox.ttf'
        font20 = ImageFont.truetype(font_path, 26)
        font18 = ImageFont.truetype(font_path, 18)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        # uptime
        d.text((50, 0), PageInfo.uptime(), font=font18, fill="black")

        # connected users
        d.text((20, 30), PageInfo.get_connected_users(),
               font=font20, fill="black")

        # network stats
        try:
            stat = PageInfo.network('wlan0')
            d.text((58, 35), "Tx: %s" % PageInfo.bytes2human(
                stat.bytes_sent), font=font18, fill="black")
            d.text((58, 47), "Rx: %s" % PageInfo.bytes2human(
                stat.bytes_recv), font=font18, fill="black")
        except KeyError:
            # no wifi enabled/available
            pass

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageInfo(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
