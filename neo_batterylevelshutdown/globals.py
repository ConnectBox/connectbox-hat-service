# -*- coding: utf-8 -*-
# globals.py
#
# Here we have a single place to create and make available globals which
#  will be used in multiple modules

# Example to create and write the dictionary (next four lines)
#details  = {'Brand':"ConnectBox", 'Image':"connectbox_image.png", 'Font':26,'pos_x': 7,'pos_y': 0}
#with open('/usr/local/connectbox/brand.txt', 'w') as f:
#    f.write(json.dumps(details))
#    f.close()

import io
import json

# need to initialize the variables outside of the init() function
# Then the init() will fill in the correct values

device_type = "PH_type"
brand_name = "PH_name"
logo_image = "PH_image"
splash_x = 7
splash_y = 0
splash_font = 26

# font sizes are just specified here
font30 = 26
font20 = 19
font14 = 13
font10 = 11


def init():
  # by defining as global, the following variables can be modified
  #  by the init() function
    global device_type
    global brand_name
    global logo_image
    global splash_x
    global splash_y
    global splash_font

  # Using a dictionary and json to store Branding stuff
  # Read the dictionary
    f = open('/usr/local/connectbox/brand.txt', "r")
    data = f.read()
    js = json.loads(data)

    brand_name = js["Brand"]
    logo_image = js["Image"]
    splash_font = js["Font"]
    splash_x = js["pos_x"]
    splash_y = js["pos_y"]
    f.close()
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
    f = io.open("/proc/cpuinfo", mode="r", encoding = 'utf-8')
    filx = f.read()

    if ("Raspberry" in filx):
        if ("Compute Module" in filx):
            device_type = "CM"
        else:           #all other Raspberry Pi version other than compute modules
            device_type = "PI"
    f.close()
