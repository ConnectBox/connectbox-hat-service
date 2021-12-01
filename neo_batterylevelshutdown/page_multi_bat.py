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
            bat_exists = self.axp.battery_exists
            have_axp209 = True
        except OSError:
            have_axp209 = False

        # draw text, full opacity
        if bat_exists:
            d.text((68, 1),(str(averageBat()/1000)), font=font20, fill="black")
        else:
            d.text((68, 1),("0.000"), font=font20, fill="black")
            
        # page_multi_bat.py should only be called if we have CM4 HAT, which includes AXP209
        #  so we should ALWAYS have "have_axp209" true (unless our HAT is broken)
        if have_axp209:
            if self.axp.power_input_status.acin_present:
            # charging -- cover the "out" arrow
                d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
            else:
                # discharging --- cover the charging symbol & "in" arrow
                d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
                d.rectangle((0, 4, 14, 14), fill="white")     # "in" arrow

        if bat_exists:
            battery_voltage = averageBat()
            # calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            # get the percent filled and draw a rectangle
            percent = min(averageFuel(), 100)
            if percent < 10:
                d.rectangle((20, 5, 22, 12), fill="black")
                d.text((15, 2), "!", font=font14, fill="black")
            else:
                # start of battery level= 20px, end = 38px
                x = int((38 - 20) * (percent / 100)) + 20
                # print("X:" + str(x))
                d.rectangle((20, 5, x, 12), fill="black")
        else:
            battery_voltage = 0
            percent = 0    
            # cross out the battery
            d.line((20, 5, 38, 12), fill="black", width=2)
            d.line((20, 12, 38, 5), fill="black", width=2)

        # Read voltages of all 4 battery positions from the ATTiny
        # Any voltage < 0.5V (500 mV) or > 6000 we will call noise 
        #  and display battery voltage 0
        # Note that readBat() function accepts battery numbers 1 -> 4 (not 0 -> 3)
        v_bat = [0,0,0,0]
        for n in range(4):
            v_bat[n] = readBat(n+1)
            if (v_bat[n] < 500) or (v_bat[n] > 6000):
                v_bat[n] = 0

        d.text((10, 18),(str(v_bat[0]/1000)), font=font20, fill="black")    # battery #1
        d.text((10, 42),(str(v_bat[1]/1000)), font=font20, fill="black")    # battery #2
        d.text((75, 18),(str(v_bat[2]/1000)), font=font20, fill="black")    # battery #3
        d.text((75, 42),(str(v_bat[3]/1000)), font=font20, fill="black")    # battery #4

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageMultiBat(get_device(), axp209.AXP209()).draw_page()
    except KeyboardInterrupt:
        pass
