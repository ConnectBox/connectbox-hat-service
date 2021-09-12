# -*- coding: utf-8 -*-


"""
===========================================
  branding.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  DorJamJr - July 2021
===========================================
"""

import neo_batterylevelshutdown.globals as globals


# Maximum 10 characters
global  brand_name
# png file of logo 
global  logo_image


class Brand:

    def name(self):
        brand_name = 'ConnectBox'
        return "%s" % brand_name

    def splash(self):
        a = Brand.name(self)
        position_x = 7
        position_y = 0
        font = 26
        return (a, font, position_x, position_y)
    

    def image(self):
        logo_image = 'connectbox_logo.png'
        return "%s" % logo_image
