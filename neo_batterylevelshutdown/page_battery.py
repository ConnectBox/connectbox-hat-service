# -*- coding: utf-8 -*-

"""
===========================================
  page_battery.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

import os.path
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import axp209
from .HAT_Utilities import get_device


class PageBattery:
    def __init__(self, device, axp):
        self.device = device
        self.axp = axp

    def draw_page(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        # find out if the unit is charging or not
        # get an image
        img_path = dir_path + '/assets/battery_page.png'

        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/connectbox.ttf'
        font18 = ImageFont.truetype(font_path, 18)
        font14 = ImageFont.truetype(font_path, 14)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        # See if we have a responsive AXP209
        try:
            _ = self.axp.battery_exists
            have_axp209 = True
        except OSError:
            have_axp209 = False

        # draw text, full opacity
        if have_axp209:
            d.text((5, 42), "%.0f" %
                   int(self.axp.battery_voltage), font=font18, fill="black")
            d.text((52, 42), "%.1f" %
                   self.axp.internal_temperature, font=font18, fill="black")
        else:
            # Act like there's no battery present
            d.text((5, 42), "%.0f" %
                   -1, font=font18, fill="black")
            d.text((52, 42), "%.1f" %
                   -1, font=font18, fill="black")

        if have_axp209 and self.axp.power_input_status.acin_present:
            # charging
            # cover the out arrow
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            # percent charge left
            d.text((50, 1), "%.0f%%" %
                   self.axp.battery_gauge, font=font18, fill="black")
            d.text((94, 42), "%.0f" %
                   self.axp.battery_charge_current, font=font18, fill="black")
        else:
            # discharging or AXP209 not present i.e. not doing it's job
            # cover the charging symbol & in arrow
            d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
            d.rectangle((0, 4, 14, 14), fill="white")  # in arrow
            # percent charge left
            if have_axp209:
                d.text((63, 1), "%.0f%%" %
                       self.axp.battery_gauge, font=font18, fill="black")
                d.text((94, 42), "%.0f" %
                       self.axp.battery_discharge_current,
                       font=font18, fill="black")
            else:
                d.text((63, 1), "%.0f%%" %
                       -1, font=font18, fill="black")
                d.text((94, 42), "%.0f" %
                       -1, font=font18, fill="black")

        # draw battery fill lines
        if not have_axp209 or not self.axp.battery_exists:
            # cross out the battery
            d.line((20, 5, 38, 12), fill="black", width=2)
            d.line((20, 12, 38, 5), fill="black", width=2)
        else:
            # get the percent filled and draw a rectangle
            percent = self.axp.battery_gauge
            if percent < 10:
                d.rectangle((20, 5, 22, 12), fill="black")
                d.text((15, 2), "!", font=font14, fill="black")
            else:
                # start of battery level= 20px, end = 38px
                x = int((38 - 20) * (percent / 100)) + 20
                # print("X:" + str(x))
                d.rectangle((20, 5, x, 12), fill="black")

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageBattery(get_device(), axp209.AXP209()).draw_page()
    except KeyboardInterrupt:
        pass
