# -*- coding: utf-8 -*-

"""Console script for neo_batterylevelshutdown."""

# Modified 11/05/19 JRA to detect no battery unit by asking the AXP209 whether battery exists
# AXP209 code comes from github.com/artizirk/python-axp209

import logging
import axp209
import click
import os
import RPi.GPIO as GPIO  # pylint: disable=import-error
import neo_batterylevelshutdown.globals as globals
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
import neo_batterylevelshutdown.HAT_Utilities as utilities

def getHATClass():
    logging.debug("Entering get Hat Class")
    # We assume the HAT is not present if we're unable to setup the pin
    #  or read from it. That's the safe option and means that we won't
    #  immediately shutdown devices that don't have a HAT if we've incorrect
    #  detected the presence of a HAT
    d = 0
    try:
        # See if we can find an OLED
        utilities.get_device()
    except OSError:
        # No OLED. Treat it as a DummyHAT
        logging.debug("No OLED detected, We are retuning a Dummy HAT")
        return hats.DummyHAT

    logging.debug("Ok we passed the utiities.get.device() for the display")
# Express all pin numbers in BCM nomenclature for compatibility with CM4
#  (which requires BCM)
# We will carry the original, NEO based names but use BCM pin numbers
#  Note that PA1 is used only for version testing in NEO, so for RPi (PI and CM4)
#   versions we specify an un-connected pin... GPIO25
#   PA0 only used on HAT7 for OTG sense... spec un-connected pin on others
    if globals.device_type == "NEO":
        PA6 = 12    #PA6    Amber LED pin #
        PA1 = 22    #PA1    Test for HAT 4.6.7 (all other HATs have this pin unconnected) pin #
        PG11 = 7    #PG11   Test of HAT 7 pin #
        PA0 = 11    #PA0    OTG sense (HAT7), not used on others pin #
    if globals.device_type == "CM":
        PA6 = 6     #GPIO6/30
        PA1 = 25    #GPIO25/41
        PG11 = 4    #GPIO4/54   Actually GPIO4 is PB2 which will be HIGH on CM4 HAT
        PA0 = 17    #GPIO17/50
    if globals.device_type == "PI":
        PA6 = 18    #device is Pi GPIO18
        PA1 = 23    #GPIO25
        PG11 = 4    #GPIO4
        PA0 = 17    #GPIO17

    GPIO.setup(PA6,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PG11,GPIO.IN, pull_up_down=GPIO.PUD_UP)
    if GPIO.input(PA6) == GPIO.LOW:
        logging.debug("NEO HAT not detected")
        return hats.DummyHAT
    logging.debug("passed GPIO no hat test looking for AXP209")
    try:
        axp = axp209.AXP209(globals.port)
    # moved the battexists = axp.battery_exists test to the individual battery display pages
        axp.close()
        # AXP209 found... we have HAT from Q3Y2018 or later
        # Test PA1...
        #    HIGH => Q3Y2018 == HAT 4.6.7
        #    LOW =>          == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; HAT 7; CM4
        # Test PG11...
        #    HIGH => Q4Y2018 == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; CM4
        #    LOW  => Q3Y2021 == HAT 7

        GPIO.setup(PA1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if GPIO.input(PA1) == GPIO.LOW:
            if (GPIO.input(PG11) == GPIO.HIGH):
            # This would include CM4 HAT as "PG11" is assigned to GPIO4
            #  and that is wired to PB2 (normally HIGH)
                logging.info("Q4Y2018 HAT Detected")
                return hats.q4y2018HAT
            else:
                logging.info("Q3Y2021 HAT Detected")
                return hats.q3y2021HAT
        else:
        # PA1 is HIGH, so this is HAT 4.6.7
            logging.info("Q3Y2018 HAT Detected")
            return hats.q3y2018HAT

    except OSError:
        # There is no AXP209 on the Q12018 HAT
        #  so this is either a real Q1Y2018 HAT or we have a bare processor
        logging.info("Q1Y2018 HAT Detected")
        return hats.q1y2018HAT
    except KeyboardInterrupt:
        pass

    return hats.DummyHAT

def call_battery():
    page_battery.PageBattery(self.display_device, self.axp)
    return

def getDisplayClass():
    logging.debug("Entering get Display Class")
    try:
        # See if we can find an OLED
        utilities.get_device()
    except:
        # No OLED. This is a standard Axp209 HAT
        logging.info("No OLED detected")
        return displays.DummyDisplay




def fixfiles(a, c):
# This function is called to fix the files and restart the network interfaces based on what we have loaded.  AP represents the Wlan that will serve as the Access point.  CI is the ethernet interface which may or may not be there
# in a standard configuration.
    logging.debug("Entering fix files")
    at = ""
    ct = ["",""]
    try:
        f = open("/usr/local/connectbox/wificonf.txt", 'r')
        at = f.read()
        ct = at.split("\n")
        f.close()
    except:
        pass
    logging.info("wificonf.txt holds "+ct[0]+" and "+ct[1]+" for passed paramaters "+a+" and "+c)
    if a in ct[0] and c in ct[1]:
        logging.info("Skipped file reconfiguration as the configuration is the same")
        return

# Lets start with the /etc/network/interface folder
    f = open('/etc/network/interfaces','r', encoding='utf-8')
    g = open('/etc/network/interfaces.tmp','w', encoding='utf-8')
    x = 0
    l = ""
    n = ""
    for y,l in enumerate(f):
        if 'wlan' in l:
            m = l.split('wlan')
            if x< 4:
                n = m[0]+a                            #insert the AP wlan
                logging.debug("on interface line were setting $1: "+n)
                x +=1
            else:
                n = m[0]+c
                logging.debug("on interface line were setting $2: "+n)
                x += 1
            while m[1][0].isnumeric():
                m[1] = m[1][1:]                   #Remove numeric characters
            n = str(n + m[1])
        else:
            n = str(l)
        g.write(n)

    f.flush()
    g.flush()
    f.close()
    g.close()
    logging.debug("we have finished the temp /etc/network/interfaces.tmp file")
# Now we are done with the /etc/netowrk/interface  file
# Lets work on the dnsmask.conf file

    f = open('/etc/dnsmasq.conf','r', encoding='utf-8')
    g = open('/etc/dnsmasq.tmp','w', encoding='utf-8')
    x = 0
    l = ""
    n = ""
    for y,l in enumerate(f):
        if 'interface=wlan' in l:
             m = l.split('interface=wlan')
             n = str(m[0]+'interface='+a)
             logging.debug("on dnsmasq were setting $1: "+n)
             x += 1
             while m[1][0].isnumeric():
                   m[1] = m[1][1:]
             n = str(n + m[1])
        else:
             n = str(l)
        g.write(n)

    f.flush()
    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/dnsmasq.tmp file")
# Now we are done with the /etc/dnsmasq.conf file
# lets move onto the hostapd.conf file

    f = open('/etc/hostapd/hostapd.conf','r', encoding='utf-8')
    g = open('/etc/hostapd/hostapd.tmp','w', encoding='utf-8')
    x = 0
    n = ""
    for y,l in enumerate(f):
        if 'interface=wlan' in l:
             m = l.split('interface=wlan')
             n = str(m[0]+'interface='+a)
             logging.debug("on hostapd were setting $1: "+n)
             x += 1
             while m[1][0].isnumeric():
                   m[1] = m[1][1:]
             n = str(n + m[1])
        else:
             n = str(l)
        g.write(n)

    f.flush()
    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/hostapd/hostapd.tmp file")

#  Now lets make sure we write out the configuration for future
    try:
        f = open("/usr/local/connectbox/wificonf.txt", 'w')
        f.write(a+"\n")
        f.write(c+"\n")
        f.write("####END####\n")
        f.flush()
        f.close()
    except:
        pass

# Now we are done with hostapd.conf

    if a != "":
         os.system("ifdown "+a)
    if c != "":
         os.system("ifdown "+c)
    os.system("systemctl stop dnsmasq.serice")
    os.system("systemctl stop networking.serice")
    os.system("systemctl stop dhcpcd.service")
    logging.info("We have taken the interfaces down now")
    os.system("mv /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.bak")
    os.system("mv /etc/dnsmasq.conf /etc/dnsmasq.bak")
    os.system("mv /etc/network/interfaces /etc/network/interfaces.bak")

    os.system("mv /etc/hostapd/hostapd.tmp /etc/hostapd/hostapd.conf")
    os.system("mv /etc/dnsmasq.tmp /etc/dnsmasq.conf")
    os.system("mv /etc/network/interfaces.tmp /etc/network/interfaces")
#    os.system("rm /etc/hostapd/hhostapd.tmp")
#    os.system("rm /etc/dnsmasq.tmp")
#    os.system("rm /etc/network/interfaces.tmp")
    logging.info("We have completed the file copy copleteions")
    os.system("systemctl start networking.service")
    os.system("systemctl start dhcpcd.service")
    os.system("systemctl start dnsmasq.service")
    if a != "":
        os.system("ifup "+a)
    if c != "":
        os.system("ifup "+c)
    logging.info("We have brought up the interfaces again")
    return 0


def getNetworkClass():
    # this module is designed to get the available interfaces and define which interface is the client facing one and which is the
    # network facing interface.  The client interface is the AP interface and is based on either RTL8812AU or RTL8812BU or RTL88192U  The
    # network facing interface will use the on board BMC wifi module as long as an AP module is present.  If no AP module is present it will become
    # the AP although this is not optimal.  But this is useful for modules such as the RaspberryPi Zero W.
    netwk=[]
    res = ""
    a = ""
    b = ""
    logging.debug("starting the get network class tool of cli.py on the battery page")
    res = os.popen("lshw -c network").read()
    i=3
    if "wlan" in res:
        r = res.split("wlan")
        while i > 1:
            if len(r) <= 1:
                a == ""
            else:
                a = r[1][0]
            if a != "":
                if r[1].find("driver="):
                    b = r[1].split("driver=")[1].split(" ")[0]             #Split out the driver from the configuration line
                    netwk.append(['wlan'+a,b])                          #add the wlan# and driver to the list
                    logging.info("found wlan driver combo, "+a+" driver: "+b)
                    a = ""
                    b = ""
                else:
                    b = "none"
            i = len(r)                                              #slice out the [0 and 1] sections of the split
            res = ""
            while i>1:
                r[len(r)-i] = r[len(r)-i+1]
                i -=1
            s = r.pop()                                           #remove the last item in the list
            i = len(r)
    logging.info("We finished the wlan lookup and arfe now going to edit the files.")
    AP = ""                                                         #access point interface
    CI = ""                                                         #client interface
    rbt = 0                                                         #reboot set to no
    if len(netwk) == 1:                                             #only one wlan interface AP only
        a = netwk[0][0]
        b = netwk[0][1]
        logging.info("single interface "+a+" with driver "+b)
        # now we need to update the files for a single AP and no client
        AP = a;
        rbt = fixfiles(AP,CI)                                       #Go for fixing all the file entries
    elif len(netwk) > 1:                                            #multiple wlan's so both AP and client interfaces
        logging.info(netwk[0][0]+" with driver "+netwk[0][1])
        logging.info(netwk[1][0]+" with driver "+netwk[1][1])
            # we have an rtl driver on this first wlan
        if "rtl" in netwk[0][1]:                                    #if we have an rtl on the first wlan we will use it for AP
            AP = netwk[0][0]
            CI = netwk[1][0]
            #regardless of what we have there since its RTL-X we will use it for AP since we have no others
        if "rtl" in netwk[1][1]:                                    #if we have an rtl on the second wlan we will use it for AP
            if AP== "":
                AP = netwk[1][0]                                    #interface 2 has the rtl and will be AP
                CI = netwk[0][0]                                    #interface 1 is on board or other andd will be the client side for network
            else:
                if "8812" in netwk[1][1] or "8192" in netwk[1][1]:
                    AP = netwk[1][0]                                #intreface 2 will be the Client network connection even if it is an rtl device
                    CI = netwk[0][0]
                else:
                    CI = netwk[1][0]
        logging.info("AP will be: "+AP+" etherneet facing is: "+CI)
        if len(netwk) >=3:
            logging.info("we have more interfaces so they must be manually managed")  # if we have more than 2 interfaces then they must be manually managed.
        rbt = fixfiles(AP,CI)                                       #Go for fixing all the file entries
    else:                                                           # we don't have even 1 interface
        logging.info("We have no wlan interfaces we can't function this way, rebooting to try to find the device")
        rbt = 1                                                     # we will reboot and try again.
    if rbt == 1:
        os.popen("reboot")
        return





@click.command()
@click.option('-v', '--verbose', is_flag=True, default=False)

def main(verbose):
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
         logging.basicConfig(level=logging.DEBUG)

#Initialize the Global Variables
    globals.init()
# Use BCM pin numbering scheme for compatibility with CM4 and use Board compatability for NEO
    if globals.device_type == "NEO": GPIO.setmode(GPIO.BOARD)
    else: GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

# Go find the netowrk interfaces and seteup the wans
    getNetworkClass()        #sets up the AP and Client interfaces
    logging.debug("Finished netowrk class")
    hatClass = getHATClass()
    logging.debug("finished hat class")
    displayClass = getDisplayClass()
    logging.debug("finished display class starting main loop")
    try:
        hatClass(displayClass).mainLoop()
    except KeyboardInterrupt:
        GPIO.cleanup()       # clean up GPIO on CTRL+C exit
    GPIO.cleanup()           # clean up GPIO on normal exit


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
