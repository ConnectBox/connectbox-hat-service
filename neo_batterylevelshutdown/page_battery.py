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
import smbus2
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import axp209
from . import globals
from .HAT_Utilities import get_device


# Start building the interactive menuing...

dev_i2c = 0x34 # for AXP209 = 0x34
#dev_i2c = 0x14  # for ATTiny88 on CM4 = 0x14
bus = smbus2.SMBus(globals.port)

class PageBattery:
    def __init__(self, device, axp):
        self.device = device
        self.axp = axp
        global bus
# Then need to create a smbus object like...

        bus = smbus2.SMBus(globals.port)   # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1), etc

# Then we can use smbus commands like... (prefix commands with "bus.") 
#
# read_byte(dev)     / reads a byte from specified device
# write_byte(dev,val)   / writes value val to device dev, current register
# read_byte_data(dev,reg) / reads byte from device dev, register reg
# write_byte_data(dev,reg,val) / write byte val to device dev, register reg 
#
# pylint: disable=too-many-locals


# handle the occassional failure of i2c read (ioctl errno 121)
    def i2c_read(device, reg):
        value = -1
        i = 1
        while (value == -1) and (i < 10):
            try:
                value = bus.read_byte_data(device, reg)
                return (value)
            except:
                i += 1
        return (-1)      # return -1 if we have 10 successive read failures      



    def draw_page(self):
        global bus
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

        # See if we have a responsive AXP209
        try:
            bat_exists = self.axp.battery_exists
            bat_voltage = self.axp.battery_voltage
            have_axp209 = True
        except OSError:
            have_axp209 = False

        # draw text, full opacity
        if have_axp209:
            if not bat_exists:
                bat_voltage = 0
            d.text((3, 44), "%.0f" %
                       int(bat_voltage), font=font20, fill="black")
            d.text((47, 44), "%.1f" %
                       self.axp.internal_temperature, font=font20, fill="black")

        else:       # no AXP209
            # Act like there's no battery present
            d.text((5, 44), "%.0f" %
                   -1, font=font20, fill="black")
            d.text((52, 44), "%.1f" %
                   -1, font=font20, fill="black")

        if have_axp209 and self.axp.power_input_status.acin_present:
            # charging
            # cover the out arrow
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            # percent charge left
            percent = self.axp.battery_gauge
            d.text((63, 2), "%.0f%%" %
                   percent, font=font20, fill="black")
            if globals.device_type == "CM":
                logging.info("Bus Battery: "+str( PageBattery.i2c_read(dev_i2c, 0x31)))
                d.text((95,2), "#%.0f" %
                   float(PageBattery.i2c_read(dev_i2c, 0x31)), font=font20, fill="black")		#Display the battery number
            d.text((97, 44), "%.0f" %
                   self.axp.battery_charge_current, font=font20, fill="black")
        else:
            # discharging or AXP209 not present i.e. not doing it's job
            # cover the charging symbol & in arrow
            d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
            d.rectangle((0, 4, 14, 14), fill="white")  # in arrow
            # percent charge left
            if have_axp209:
                # if on battery power, calculate fuel based on battery voltage
                #  Fuel = (Vbatt - 3.275)/0.00767
                # simplifies to: (Vbatt(mv) - 3275) / 7.67
                battery_voltage = self.axp.battery_voltage
                percent =  (battery_voltage - 3275) / 7.67

                d.text((63, 2), "%.0f%%" %
                       percent, font=font20, fill="black")
                d.text((97, 44), "%.0f" %
                       self.axp.battery_discharge_current,
                       font=font20, fill="black")
                if globals.device_type == "CM":
                    logging.info("Bus Battery: "+str( PageBattery.i2c_read(dev_i2c, 0x31)))
                    d.text((95,2), "#%.0f" %
                       float(PageBattery.i2c_read(dev_i2c, 0x31)), font=font20, fill="black")		#Display the battery number
            else:
                d.text((63, 2), "%.0f%%" %
                       -1, font=font20, fill="black")
                d.text((97, 44), "%.0f" %
                       -1, font=font20, fill="black")

        # draw battery fill lines
        if not have_axp209 or not self.axp.battery_exists:
            # cross out the battery
            d.line((20, 5, 38, 12), fill="black", width=2)
            d.line((20, 12, 38, 5), fill="black", width=2)
        else:
            # get the percent filled and draw a rectangle
            # percent = self.axp.battery_gauge
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
