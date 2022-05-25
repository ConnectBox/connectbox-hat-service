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
from axp209 import AXP209, AXP209_ADDRESS


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
            logging.debug("  ac: %s, battexists: %s, have_axp209: %s", acin_present, battexists, have_axp209)

            #  calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            # simplifies to: (Vbatt(mv) - 3275) / 7.67 
            if globals.device_type != "CM":
                battery_voltage = self.axp.battery_voltage
                battgauge =  (battery_voltage - 3275) / 7.67
            else:
                battery_voltage = mb_utilities.averageBat()
                battgauge = mb_utilities.averageFuel()
#               logging.debug("  type==CM: Battery Level: %s%%", battgauge)

        except OSError:
            acin_present = False
            battexists = False
            battgauge = -1
            have_axp209 = False

    # Handle the lower text separately....
        if have_axp209:
            d.text((47, 44), "%.1f" %
                    self.axp.internal_temperature, font=font20, fill="black")
            if battexists:
                d.text((3, 44), "%.0f" %
                       int(battery_voltage), font=font20, fill="black")
        else:    
            d.text((5, 44), "%s" %
                    "x", font=font20, fill="black")
            d.text((52, 44), "%s" %
                    "x", font=font20, fill="black")

    # now handle everything else based on state of battenxits and acin_present

        if battexists and acin_present and have_axp209:
            logging.debug("  +b  +a ")
            # charging... cover the out arrow
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            d.text((63, 2), "%.0f%%" %
                   battgauge, font=font20, fill="black")

            # multiple batteries
            if globals.device_type == "CM":
                logging.info("Bus Battery: "+str(mb_utilities.bat_number()))
                d.text((99,2), "#%.0f" %
                   float(mb_utilities.bat_number()), font=font20, fill="black")		#Display the battery number

            # charge current
            d.text((92, 44), "%.0f" %
                   self.axp.battery_charge_current, font=font20, fill="black")
                            # get the percent filled and draw a rectangle
            # percent = self.axp.battery_gauge
            if battgauge < 10:
                d.rectangle((20, 5, 22, 12), fill="black")
                d.text((15, 2), "!", font=font14, fill="black")
            else:
                # start of battery level= 20px, end = 38px
                x = int((38 - 20) * (battgauge / 100)) + 20
                d.rectangle((20, 5, x, 12), fill="black")


        if battexists and not acin_present:
            logging.debug("  +b  -a")
            # discharging... cover the charging symbol & in arrow
            d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
            d.rectangle((0, 4, 14, 14), fill="white")     # in arrow

            # percent charge left
            if have_axp209:
                d.text((63, 2), "%.0f%%" %
                       battgauge, font=font20, fill="black")
                d.text((92, 44), "%.0f" %
                       self.axp.battery_discharge_current,
                       font=font20, fill="black")

                # multiple batteries    
                if globals.device_type == "CM":
                    logging.info("Bus Battery: "+str(mb_utilities.bat_number()))
                    d.text((99,2), "#%.0f" %
                        float(mb_utilities.bat_number()), font=font20, fill="black")		#Display the battery number

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


            else:
                d.text((63, 2), "%s%%" %
                       "x", font=font20, fill="black")
                d.text((92, 44), "%s" %
                       "x", font=font20, fill="black")

        # we are running on ac
        if not battexists and acin_present:  
            logging.debug("    -b +a")  
            # cross out the battery
            d.line((20, 5, 38, 12), fill="black", width=2)
            d.line((20, 12, 38, 5), fill="black", width=2)

            #  no current in or out of battery... cover the out and in arrows
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            d.rectangle((0, 4, 14, 14), fill="white")   # in arrow



            # show the AC voltage and current
            if have_axp209:
                #show AC voltage
                hexval = self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x56)
                hexval = (hexval << 4)
                hexval += self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x57)
                ac_voltage = hexval * 1.7     # per AXP209 section 9.7, lsb = 1.7 mV
                d.text((3, 44), "%.0f" %
                    ac_voltage, font=font20, fill="black")                

                # show the AC current
                hexval = self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x58)
#                logging.debug("   hexval 0x58: " +str(hexval))
                hexval = (hexval << 4)
                hexval += self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x59)
                ac_current = hexval * 0.625         # per AXP209 section 9.7, lsb = 0.625 mA
#                logging.debug("  ac_current: " + str(ac_current))
                d.text((92, 44), "%.0f" %
                       ac_current, font=font20, fill="black")
 
        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageBattery(get_device(), axp209.AXP209()).draw_page()
    except KeyboardInterrupt:
        pass
