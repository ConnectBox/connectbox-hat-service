# -*- coding: utf-8 -*-

"""
===========================================
  page_main.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

import os.path
import subprocess
from PIL import Image, ImageFont, ImageDraw
import axp209
from .HAT_Utilities import get_device, GetReleaseVersion


class PageMain:
    def __init__(self, device, axp):
        self.device = device
        self.axp = axp

    @staticmethod
    def get_connected_users():
        c = subprocess.run(['iw', 'dev', 'wlan0', 'station',
                            'dump'], stdout=subprocess.PIPE)
        connected_user_count = len([line for line in c.stdout.decode(
            "utf-8").split('\n') if line.startswith("Station")])
        return "%s" % connected_user_count

    @staticmethod
    def get_cpu_temp():
        with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as f:
            tempC = f.readline()
        return int(tempC)/1000

    def draw_page(self):
        # get an image
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/main_page.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/connectbox.ttf'
        font30 = ImageFont.truetype(font_path, 30)
        font20 = ImageFont.truetype(font_path, 20)
        font14 = ImageFont.truetype(font_path, 14)

        # get a drawing context
        d = ImageDraw.Draw(txt)

        # ConnectBox Banner
        d.text((2, 0), 'ConnectBox', font=font30, fill="black")
        # Image version name/number
        d.text((38, 32), GetReleaseVersion(), font=font14, fill="black")

        # connected users
        d.text((13, 35), PageMain.get_connected_users(),
               font=font20, fill="black")

        try:
            acin_present = self.axp.power_input_status.acin_present
        except:
            acin_present = False

        if not acin_present:
            # not charging - cover up symbol
            d.rectangle((64, 48, 71, 61), fill="white")  # charge symbol

        # draw battery fill lines
        try:
            battexists = self.axp.battery_exists
        except:
            battexists = False
        if not battexists:
            # cross out the battery
            d.line((37, 51, 57, 58), fill="black", width=2)
            d.line((37, 58, 57, 51), fill="black", width=2)
        else:
            # get the percent filled and draw a rectangle
            try:
                battgauge = self.axp.battery_gauge
            except:
                battgauge = -1

            if battgauge < 10:
                d.rectangle((37, 51, 39, 58), fill="black")
                d.text((43, 51), "!", font=font14, fill="black")
            else:
                # start of battery level= 37px, end = 57px
                x = int((57 - 37) * (battgauge / 100)) + 37
                d.rectangle((37, 51, x, 58), fill="black")

        # percent charge left
        d.text((75, 49), "%.0f%%" % battgauge,
               font=font14, fill="black")
        # cpu temp
        d.text((105, 49), "%.0fC" % PageMain.get_cpu_temp(),
               font=font14, fill="black")

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageMain(get_device(), axp209.AXP209()).draw_page()
    except KeyboardInterrupt:
        pass
