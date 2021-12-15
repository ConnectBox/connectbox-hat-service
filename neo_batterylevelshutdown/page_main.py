# -*- coding: utf-8 -*-

"""
===========================================
  page_main.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.1
  DorJamJr - July 2021
===========================================
"""
import logging
import os
import subprocess
import smbus2
from PIL import Image, ImageFont, ImageDraw
import axp209
import neo_batterylevelshutdown.globals as globals
from .HAT_Utilities import get_device, GetReleaseVersion



# Start building the interactive menuing...

#dev_i2c = 0x34 # for AXP209 = 0x34
dev_i2c = 0x14  # for ATTiny88 on CM4 = 0x14
bus = smbus2.SMBus(0)



class PageMain:
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

 #handle the occassional failure of i2c read (ioctl errno 121)
    @staticmethod
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


    @staticmethod
    def averageBat():
        global bus
        global dev_i2c
        bat = 0
        for reg in range (0x21, 0x29, 2):
            value = PageMain.i2c_read(dev_i2c, reg)
            value += (PageMain.i2c_read(dev_i2c, reg+1)) * 256
            bat += value
        bat = bat / PageMain.i2c_read(dev_i2c,  0x30)
        logging.info("Battery average is: "+str(bat))
        return(bat)

    @staticmethod
    def averageFuel():
        global bus
        global dev_i2c
        fuel = 0
        for reg in range (0x41, 0x45, 1):
             fuel += PageMain.i2c_read(dev_i2c, reg)
        fuel = fuel / (PageMain.i2c_read(dev_i2c, 0x30))
        fuel = round(fuel, 0)
        return(fuel)


    @staticmethod
    def get_connected_users():
        c = subprocess.run(['iw', 'dev', globals.clientIF, 'station',
                            'dump'], stdout=subprocess.PIPE)
        connected_user_count = len([line for line in c.stdout.decode(
            "utf-8").split('\n') if line.startswith("Station")])
        return "%s" % connected_user_count

    @staticmethod
    def get_cpu_temp():
        with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as f:
            tempC = f.readline()
        return int(tempC)/1000

    # pylint: disable=too-many-locals
    def draw_page(self):
        global bus
        try: os.remove('/usr/local/connectbox/PauseMount')
        except:
           pass
        # get an image
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/main_page.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))


        # get a drawing context
        d = ImageDraw.Draw(txt)
        name = globals.brand_name
        font = globals.splash_font
        x = globals.splash_x
        y = globals.splash_y

        logging.info("Branding Name : "+ globals.brand_name)          # test element for log  

        # get a font
        font_path = dir_path + '/assets/connectbox.ttf'
        font30 = ImageFont.truetype(font_path, globals.font30)
        font20 = ImageFont.truetype(font_path, globals.font20)
        font14 = ImageFont.truetype(font_path, globals.font14)

        d.text((x, y), name, font=font30, fill="black")
        # Image version name/number
        d.text((38, 32), GetReleaseVersion(), font=font14, fill="black")

        # connected users
        d.text((13, 35), PageMain.get_connected_users(),
               font=font20, fill="black")

        try:
            # The AXP209 can disappear - degrade gracefully if that
            #  happens.
            acin_present = self.axp.power_input_status.acin_present
            battexists = self.axp.battery_exists
            if acin_present:
                if globals.device_type != "CM":
                    battgauge = self.axp.battery_gauge
                    battery_voltage = self.axp.battery_voltage
                else:
                    battgauge = PageMain.averageFuel()
                    battery_voltage = PageMain.averageBat()
            else:
            # if on battery power, calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            # simplifies to: (Vbatt(mv) - 3275) / 7.67 
                if globals.device_type != "CM":
                    battery_voltage = self.axp.battery_voltage
                    battgauge =  (battery_voltage - 3275) / 7.67
                else:
                    battery_voltage = PageMain.averageBat()
                    battgauge = PageMain.averageFuel()
        except OSError:
            acin_present = False
            battexists = False
            battgauge = -1

        if not acin_present:
            # not charging - cover up symbol
            d.rectangle((64, 48, 71, 61), fill="white")  # charge symbol

        # draw battery fill lines
        if not battexists:
            # cross out the battery
            d.line((37, 51, 57, 58), fill="black", width=2)
            d.line((37, 58, 57, 51), fill="black", width=2)
        else:
            # get the percent filled and draw a rectangle
            if battgauge < 10:
                d.rectangle((37, 51, 39, 58), fill="black")
                d.text((43, 51), "!", font=font14, fill="black")
            else:
                # start of battery level= 37px, end = 57px
                battgauge = min(battgauge, 100)
                logging.info("battery gauge is "+str( battgauge ))

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


