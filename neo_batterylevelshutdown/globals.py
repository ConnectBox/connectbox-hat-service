# globals.py
#
# Here we have a single place to create and make available globals which
#  will be used in multiple modules

# Example to create and write the dictionary (next four lines)
#details  = {'Brand':"ConnectBox", 'Image':"connectbox_image.png", 'Font':26,'pos_x': 7,'pos_y': 0}
#with open('/usr/local/connectbox/brand.txt', 'w') as f:
#    f.write(json.dumps(details))
#    f.close()


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


def init():
  # Using a dictionary and json to store Branding stuff
  # Read the dictionary
  with open('/usr/local/connectbox/brand.txt') as f:
    data = f.read()
  js = json.loads(data)

  brand_name = js["Brand"]
  logo_image = js["Image"]
  splash_font = js["Font"]
  splash_x = js["pos_x"]
  splash_y = js["pos_y"]

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

 
# set font sizes to work with current PIL calculations for ttf
  font30 = 26
  font20 = 19
  font14 = 13
  font10 = 11
