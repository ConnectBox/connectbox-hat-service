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
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import axp209
import neo_batterylevelshutdown.globals
from neo_batterylevelshutdown.HAT_Utilities import get_device
import neo_batterylevelshutdown.multiBat_Utilities as mb_utilities



class PageMulti_Bat:
    def __init__(self, device, axp):
        self.device = device
        self.axp = axp

    # pylint: disable=too-many-locals
    def draw_page(self):

        dir_path = os.path.dirname(os.path.abspath(__file__))
        # find out if the unit is charging or not
        # get an image
        img_path = dir_path + '/assets/multi_bat.png'
        check_path = dir_path + '/assets/check5.png'
        box_path = dir_path + '/assets/box.png'

        base = Image.open(img_path).convert('RGBA')
        check_img = Image.open(check_path).convert('RGBA')
        box_img = Image.open(box_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/HaxM-10.pil'
        font10 = ImageFont.load(font_path)
        font_path = dir_path + '/assets/HaxM-12.pil'
        font14 = ImageFont.load(font_path)
        font_path = dir_path + '/assets/HaxM-13.pil'
        font20 = ImageFont.load(font_path)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        # See if we have a responsive AXP209
        try:
            bat_exists = self.axp.battery_exists
            have_axp209 = True
        except OSError:
            have_axp209 = False
            bat_exists = False          # axp209 no help, so call it "no battery"

        # draw text, full opacity
        if bat_exists:
        # format with 2 decimals
            b_voltage = mb_utilities.averageBat()/1000
            v_string = "{:.2f}V"                
            d.text((68, 2),(v_string.format(b_voltage)), font=font14, fill="black")
        else:
            d.text((68, 2),("0.00V"), font=font14, fill="black")
           
        # page_multi_bat.py should only be called if we have CM4 HAT, which includes AXP209
        #  so we should ALWAYS have "have_axp209" true (unless our HAT is broken)
        if (self.axp.power_input_status.acin_present and have_axp209):
        # charging -- cover the "out" arrow
            d.rectangle((47, 4, 62, 14), fill="white")  # out arrow
        else:
            # discharging --- cover the charging symbol & "in" arrow
            d.rectangle((119, 0, 127, 16), fill="white")  # charge symbol
            d.rectangle((0, 4, 14, 14), fill="white")     # "in" arrow

        if bat_exists:
            battery_voltage = mb_utilities.averageBat()
            # calculate fuel based on battery voltage
            #  Fuel = (Vbatt - 3.275)/0.00767
            # get the percent filled and draw a rectangle
            percent = min(mb_utilities.averageFuel(), 100)
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
        # Note that bat_voltage() function accepts battery numbers 1 -> 4 (not 0 -> 3)
        v_bat = ["0V","0V","0V","0V"]
        for n in range(4):
            voltage = mb_utilities.bat_voltage(n+1)
            if (voltage < 500) or (voltage > 6000):
                voltage = 0
            # format with 2 decimals
            b_voltage = voltage/1000
            v_string = "{:.2f}V"
            v_bat[n] = v_string.format(b_voltage)

        d.text((3, 19),"1", font=font10, fill="black")    # battery #1
        d.text((17, 23),v_bat[0], font=font14, fill="black")    # battery #1
        d.text((3, 42),"2", font=font10, fill="black")    # battery #1
        d.text((17, 46),v_bat[1], font=font14, fill="black")    # battery #2
        d.text((67, 19),"3", font=font10, fill="black")    # battery #1
        d.text((82, 23),v_bat[2], font=font14, fill="black")    # battery #3
        d.text((67, 42),"4", font=font10, fill="black")    # battery #1
        d.text((82, 46),v_bat[3], font=font14, fill="black")    # battery #4

        # find batteries in use and add marker to display to indicate those used
        glyph = [box_img,box_img,box_img,box_img]           # set empty list
        in_use_map = mb_utilities.get_in_use()
        for n in range (4):
            if (((in_use_map >> n) & 0x01) > 0):
                glyph[n] = check_img
        d.bitmap((3,29),glyph[0],fill="black")
        d.bitmap((3,52),glyph[1],fill="black")
        d.bitmap((67,29),glyph[2],fill="black")
        d.bitmap((67,52),glyph[3],fill="black")



        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageMultiBat(get_device(), axp209.AXP209()).draw_page()
    except KeyboardInterrupt:
        pass
