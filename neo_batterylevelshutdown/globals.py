# -*- coding: utf-8 -*-
# globals.py
#
# Here we have a single place to create and make available globals which
#  will be used in multiple modules

# To easily create brand.txt, use the tool BrandCreationTool.py

import io
import json
import signal
from . import page_battery
from .HAT_Utilities import get_device

# need to initialize the variables outside of the init() function
# Then the init() will fill in the correct values

device_type = "PH_type"
brand_name = "PH_name"
logo_image = "PH_image"
splash_x = 7
splash_y = 0
splash_font = 26
enable_mass_storage = 0
screen_enable = [1,1,1,1,1,1,1,1,1,1,1,1,1]

# font sizes are just specified here
font30 = 26
font20 = 19
font14 = 13
font10 = 11
g_device = "g_serial"

def call_battery():
    page_battery.PageBattery(self.display_device, self.axp)



def init(self, hat_class):
  # by defining as global, the following variables can be modified
  #  by the init() function
    global device_type
    global brand_name
    global logo_image
    global splash_x
    global splash_y
    global splash_font
    global enable_mass_storage
    global screen_enable
    global g_device
    global port

  # Using a dictionary and json to store Branding stuff
  # Read the dictionary
    f = open('/usr/local/connectbox/brand.txt', "r")
    data = f.read()
    f.close()
    js = json.loads(data)

# May want to put some checks in to allow fields to be missing and
#  if so, revert to defaults...

    brand_name = js["Brand"]
    logo_image = js["Image"]
    splash_font = js["Font"]
    splash_x = js["pos_x"]
    splash_y = js["pos_y"]

    # Just in case our brand.txt doesn't have these parameters...
    #   (for any that are missing, just keep the defaults)
    try:
        enable_mass_storage = js["Enable_MassStorage"]
    except:
        pass
    try:        
        screen_enable = js["Screen_Enable"]
    except:
        pass
    try:    
        g_device = js["g_device"]
    except:
        pass    

# check that the brand name eg: hostname hasn't changed.
# if it did we need to update the brand and the hostname
    f = io.open('/etc/hostname', mode="r", encoding='utf-8')
    bname = f.read().rstrip()
    f.close()
    if (bname.lower() != brand_name.lower()):
        brand_name = bname 
        js["Brand"] = bname 
        f = open("/usr/local/connectbox/brand.txt", 'w')
        f.write(json.dumps(js))
        f.close() 


  #find and set device_type global
    device_type = "NEO"
    port = 0
    f = io.open("/proc/cpuinfo", mode="r", encoding = 'utf-8')
    filx = f.read()

    if ("Raspberry" in filx):
        if ("Compute Module" in filx):
            device_type = "CM"
            port = 10
        else:           #all other Raspberry Pi version other than compute modules
            device_type = "PI"
            port = 1
    f.close()
    self.hat = hat_class
    # rename this.... perhaps it doesn't even need to be stored
    self.axp = self.hat.axp   # powerManagementDevice
    self.display_type = 'OLED'
    self.display_device = get_device()
    signal.signal(signal.SIGUSR1, call_battery)
