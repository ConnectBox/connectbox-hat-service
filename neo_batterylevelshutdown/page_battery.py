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
import logging
import os.path
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import axp209
from . import globals
from .HAT_Utilities import get_device
import neo_batterylevelshutdown.multiBat_Utilities as mb_utilities


# Start building the interactive menuing...



dev_i2c = 0x34 # for AXP209 = 0x34
#dev_i2c = 0x14  # for ATTiny88 on CM4 = 0x14


class PageBattery:
    def __init__(self, device, axp):
        self.device = device
        self.axp = axp

# pylint: disable=too-many-locals

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
        font_path = dir_path + '/assets/HaxM-12.pil'
        font14 = ImageFont.load(font_path)
        font_path = dir_path + '/assets/HaxM-13.pil'
        font20 = ImageFont.load(font_path)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        try:
            # The AXP209 can disappear - degrade gracefully if that
            #  happens.
            acin_present = self.axp.power_input_status.acin_present
            battexists = self.axp.battery_exists
            have_axp209 = True

            #  calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            # simplifies to: (Vbatt(mv) - 3275) / 7.67 
            if globals.device_type != "CM":
                battery_voltage = self.axp.battery_voltage
                battgauge =  (battery_voltage - 3275) / 7.67
            else:
                battery_voltage = mb_utilities.averageBat()
                battgauge = mb_utilities.averageFuel()
                logging.debug("  type==CM: Battery Level: %s%%", battgauge)

        except OSError:
            acin_present = False
            battexists = False
            battgauge = -1
            have_axp209 = False

        # draw text, VOLTAGE & TEMPERATURE, full opacity
        if have_axp209:
            d.text((3, 44), "%.0f" %
                       int(battery_voltage), font=font20, fill="black")
            d.text((47, 44), "%.1f" %
                       self.axp.internal_temperature, font=font20, fill="black")

        else:       # no AXP209
            # Act like there's no battery present
            d.text((5, 44), "%.0f" %
                   -1, font=font20, fill="black")
            d.text((52, 44), "%.1f" %
                   -1, font=font20, fill="black")

        # CHARGING - COVER THE BATTERY OUT ARROW
        #  Display Fuel, Battery Number (for CM4), Charge Current
        if have_axp209 and self.axp.power_input_status.acin_present:
            # charging
            # cover the out arrow
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            d.text((63, 2), "%.0f%%" %
                   battgauge, font=font20, fill="black")
            if globals.device_type == "CM":
                logging.info("Bus Battery: "+str(mb_utilities.bat_number()))
                d.text((95,2), "#%.0f" %
                   float(mb_utilities.bat_number()), font=font20, fill="black")		#Display the battery number
            d.text((92, 44), "%.0f" %
                   self.axp.battery_charge_current, font=font20, fill="black")

        # DISCHARGING - COVER THE BATTERY IN ARROW
        #  Display Fuel, Battery Number (CM4), Battery Current    
        else:
            # discharging or AXP209 not present i.e. not doing it's job
            # cover the charging symbol & in arrow
            d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
            d.rectangle((0, 4, 14, 14), fill="white")  # in arrow
            # percent charge left
            if have_axp209:
                d.text((63, 2), "%.0f%%" %
                       battgauge, font=font20, fill="black")
                d.text((92, 44), "%.0f" %
                       self.axp.battery_discharge_current,
                       font=font20, fill="black")
                if globals.device_type == "CM":
                    logging.info("Bus Battery: "+str(mb_utilities.bat_number()))
                    d.text((95,2), "#%.0f" %
                       float(mb_utilities.bat_number()), font=font20, fill="black")		#Display the battery number
            else:
                d.text((63, 2), "%.0f%%" %
                       -1, font=font20, fill="black")
                d.text((92, 44), "%.0f" %
                       -1, font=font20, fill="black")

        # draw battery fill lines
        if not have_axp209 or not self.axp.battery_exists:
            # cross out the battery
            d.line((20, 5, 38, 12), fill="black", width=2)
            d.line((20, 12, 38, 5), fill="black", width=2)
        else:
            # get the percent filled and draw a rectangle
            # percent = self.axp.battery_gauge
            if battgauge < 10:
                d.rectangle((20, 5, 22, 12), fill="black")
                d.text((15, 2), "!", font=font14, fill="black")
            else:
                # start of battery level= 20px, end = 38px
                x = int((38 - 20) * (battgauge / 100)) + 20
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
