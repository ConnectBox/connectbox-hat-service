# globals.py
#
# Here we have a single place to create and make available globals which
#  will be used in multiple modules
import json

global device_type
global font30
global font20
global font14
global font10
global brand_name
global logo_image
global splash_x
global splash_y
global splash_font

brand = ['ConnectBox', "connectbox_image.png", 26, 7, 0]

#find and set device_type global
device_type = "NEO"
with open("/proc/cpuinfo", encoding = 'utf8') as f:
  filx = f.read()
  if ("Raspberry" in filx):
    if ("Compute Module" in filx):
       device_type = "CM"
    else:           #all other Raspberry Pi version other than compute modules
       device_type = "PI"
  f.close()

with open('/etc/hostname', "rw", encoding='utf-8') as f:
  brand_name = f.read()
  brand_name = brand_name.rstrip()
  f.close()
with open('/usr/local/connectbox/brand.txt', "rw") as f:
  brand = json.load(f)
  brand[0] = brand_name
  logo_image = brand[1]
  json.dump(brand,f)
  f.close()

# set font sizes to work with current PIL calculations for ttf
  font30 = 26
  font20 = 19
  font14 = 13
  font10 = 11
  splash_font = brand[2]
  splash_x = brand[3]
  splash_y = brand[4]
