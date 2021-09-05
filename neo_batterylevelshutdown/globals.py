# globals.py
# 
# Here we have a single place to create and make available globals which
#  will be used in multiple modules


def init():
    global device_type
    device_type = "NEO"
    with open("/proc/cpuinfo", encoding = 'utf8') as f:
        filx = f.read()
        if ("Raspberry" in filx):
            if ("Compute Module" in filx):
                device_type = "CM"
            else:           #all other Raspberry Pi version other than compute modules
                device_type = "PI"
    f.close()
