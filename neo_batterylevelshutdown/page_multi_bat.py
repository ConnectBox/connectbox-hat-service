# -*- coding: utf-8 -*-

"""
===========================================
  page_multi-bat.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""

import os.path
import logging
import smbus2
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import axp209
from . import globals
from .HAT_Utilities import get_device

# Start building the interactive menuing...

# for AXP209 = 0x34
# for ATTiny88 on CM4 = 0x14
dev_i2c = 0x14
bus = smbus2.SMBus(0)


# handle the occassional failure of i2c read (ioctl errno 121)
def i2c_read(device, reg):
    global bus

    value = -1
    i = 1
    while (value == -1) and (i < 10):
        try:
            value = bus.read_byte_data(device, reg)
            return (value)
        except:
            i += 1
    return (-1)      # return -1 if we have 10 successive read failures      

def averageBat():
    global bus
    global dev_i2c
    bat = 0
    for reg in range (0x21, 0x29, 2):
         value = i2c_read(dev_i2c, reg)
         value += (i2c_read(dev_i2c, reg+1)) * 256
         bat += value
    bat = bat / (i2c_read(dev_i2c, 0x30))
    bat = round(bat, 0)
    return(bat)

def averageFuel():
    global bus
    global dev_i2c
    fuel = 0
    for reg in range (0x41, 0x45, 1):
         fuel += i2c_read(dev_i2c, reg)
    fuel = fuel / (i2c_read(dev_i2c, 0x30))
    fuel = round(fuel, 0)
    return(fuel)


def readBat(x):
# reading battery (valid 1 - 4) for their voltage
# read the 5 volt input at 5

    global bus
    global dev_i2c
    if x>0 and x<5:
        x -= 1 
        reg= 0x21+(x*2)
        logging.debug("read battery %i register start %i ", x+1, reg)
        value = i2c_read(dev_i2c, reg)
        value += (i2c_read(dev_i2c, reg+1)) * 256
    else: value = 0
    return(value)

def readfuel(x):
# reading battery (valid 1 - 4 ) for the fuel

    global bus
    global dev_i2c
    if x>0 and x<5:
        x -= 1 
        reg= 0x41+x
        logging.debug("read battery %i fuel register start %i ", x+1, reg)
        fuel = i2c_read(dev_i2c, reg)
    else: fuel = 0
    return(fuel)



class PageMulti_Bat:
    def __init__(self, device, axp):
        self.device = device
        self.axp = axp
        global bus
        global dev_i2c
# Then need to create a smbus object like...
        bus = smbus2.SMBus(globals.port)    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1), etc

# Then we can use smbus commands like... (prefix commands with "bus.") 
#
# read_byte(dev)     / reads a byte from specified device
# write_byte(dev,val)   / writes value val to device dev, current register
# read_byte_data(dev,reg) / reads byte from device dev, register reg
# write_byte_data(dev,reg,val) / write byte val to device dev, register reg 
#


    # pylint: disable=too-many-locals
    def draw_page(self):
#        if globals.device_type != "NEO":
#           return

        global bus
        global dev_i2c
        dir_path = os.path.dirname(os.path.abspath(__file__))
        # find out if the unit is charging or not
        # get an image
        img_path = dir_path + '/assets/multi_bat.png'

        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/connectbox.ttf'
        font20 = ImageFont.truetype(font_path, globals.font20)
        font14 = ImageFont.truetype(font_path, globals.font14)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        # See if we have a responsive AXP209
        try:
            _ = self.axp.battery_exists
            have_axp209 = True
        except OSError:
            have_axp209 = False

        # draw text, full opacity
        d.text((68, 1),(str(averageBat()/1000)), font=font20, fill="black")

        if have_axp209 and self.axp.power_input_status.acin_present:
            # charging
            # cover the out arrow
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            # percent charge left
            # if on battery power, calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            percent = averageFuel()
        else:
            # discharging or AXP209 not present i.e. not doing it's job
            # cover the charging symbol & in arrow
            d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
            d.rectangle((0, 4, 14, 14), fill="white")  # in arrow
            # percent charge left
            # if on battery power, calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            # simplifies to: (Vbatt(mv) - 3275) / 7.67 
            battery_voltage = averageBat()
            percent = averageFuel()

        # draw battery fill lines
        if not have_axp209 or not self.axp.battery_exists:
            # cross out the battery
            d.line((20, 5, 38, 12), fill="black", width=2)
            d.line((20, 12, 38, 5), fill="black", width=2)
        else:
            # get the percent filled and draw a rectangle
            # percent = self.axp.battery_gauge

            percent = min(percent, 100)
            if percent < 10:
                d.rectangle((20, 5, 22, 12), fill="black")
                d.text((15, 2), "!", font=font14, fill="black")
            else:
                # start of battery level= 20px, end = 38px
                x = int((38 - 20) * (percent / 100)) + 20
                # print("X:" + str(x))
                d.rectangle((20, 5, x, 12), fill="black")

        d.text((10, 18),(str(readBat(1)/1000)), font=font20, fill="black")
        d.text((10, 42),(str(readBat(2)/1000)), font=font20, fill="black")
        d.text((75, 18),(str(readBat(3)/1000)), font=font20, fill="black")
        d.text((75, 42),(str(readBat(4)/1000)), font=font20, fill="black")

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageMultiBat(get_device(), axp209.AXP209()).draw_page()
    except KeyboardInterrupt:
        pass
