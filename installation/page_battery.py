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

import sys
import os.path
import time
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from luma.core import cmdline, error
from luma.core.render import canvas
import axp209

from HAT_Utilities import get_device, display_settings

def draw_page(device):
    #open up the battery monitoring library
    axp = axp209.AXP209()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    #find out if the unit is charging or not
    # get an image
    img_path =  dir_path + '/assets/battery_page.png'
    if axp.battery_current_direction:
        img_path =  dir_path + '/assets/battery_charging_page.png'
    
    base = Image.open(img_path).convert('RGBA')
    fff = Image.new(base.mode, base.size, (255,) * 4)
    img = Image.composite(base, fff, base)

    # make a blank image for the text, initialized to transparent text color
    txt = Image.new('RGBA', base.size, (255,255,255,0))

    # get a font
    font_path = os.path.abspath('connectbox.ttf')
    font18 = ImageFont.truetype(font_path, 18)
    font14 = ImageFont.truetype(font_path, 14)
    # get a drawing context
    d = ImageDraw.Draw(txt)

    # draw text, full opacity
    d.text((11, 41), "%.1f" % axp.battery_voltage, font=font18, fill="black")
    d.text((52, 41), "%.1f" % axp.internal_temperature, font=font18, fill="black")
    d.text((95, 41), "%.1f" % axp.battery_charge_current, font=font18, fill="black")

    #draw battery fill lines
    if not axp.battery_exists:
        #cross out the battery
        d.line((6, 5, 24, 12), fill="black", width=2)
        d.line((6, 12, 24, 5), fill="black", width=2)
    else:
        #get the percent filled and draw a rectangle
        percent = axp.battery_gauge
        percent = 50
        if percent > 0 and percent < 10:
            d.rectangle((6, 5, 8, 12), fill="black")
            d.text((15, 2), "!", font=font14, fill="black")
        elif  percent > 10:
            x = int((24 - 6) * (percent / 100)) + 6 #start of battery level= 6px, end = 24px
            print("X:" + str(x))
            d.rectangle((6, 5, x, 12), fill="black")
    '''
    print("internal_temperature: %.2fC" % axp.internal_temperature)
    print("battery_exists: %s" % axp.battery_exists)
    print("battery_charging: %s" % ("charging" if axp.battery_charging else "done"))
    print("battery_current_direction: %s" % ("charging" if axp.battery_current_direction else "discharging"))
    print("battery_voltage: %.1fmV" % axp.battery_voltage)
    print("battery_discharge_current: %.1fmA" % axp.battery_discharge_current)
    print("battery_charge_current: %.1fmA" % axp.battery_charge_current)
    print("battery_gauge: %d%%" % axp.battery_gauge)
    '''
    axp.close()

    out = Image.alpha_composite(img, txt)
    device.display(out.convert(device.mode))

 	
def main():
    device = get_device()
    draw_page(device)
    #while True:
    #    i = 1
    return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass