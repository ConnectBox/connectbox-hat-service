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

class Brand:

    def name(self):
        # Maximum 10 characters
        brand_name = 'ConnectBox'
        return "%s" % brand_name

    def splash(self):
        brand_name = name()
        position_x = 7
        position_y = 0
        font = 26
        return (brand_name, font, postition_x, position_y)
    

    def image(self):
        logo_image = 'connectbox_logo.png'
        return "%s" % logo_image
