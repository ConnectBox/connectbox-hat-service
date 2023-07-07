# -*- coding: utf-8 -*-

"""Console script for neo_batterylevelshutdown."""

# Modified 11/05/19 JRA to detect no battery unit by asking the AXP209 whether battery exists
# AXP209 code comes from github.com/artizirk/python-axp209

import sys
import logging
import axp209
import time
import click
import os
import RPi.GPIO as GPIO  # pylint: disable=import-error
import neo_batterylevelshutdown.globals as globals
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
import neo_batterylevelshutdown.HAT_Utilities as utilities

# Global definitions for this module
hatClass = 0
progress_file = "/usr/local/connectbox/expand_progress.txt"


def getHATClass():
    logging.debug("Entering get Hat Class")
    # We assume the HAT is not present if we're unable to setup the pin
    #  or read from it. That's the safe option and means that we won't
    #  immediately shutdown devices that don't have a HAT if we've incorrect
    #  detected the presence of a HAT

    try:
        # See if we can find an OLED
        utilities.get_device()
    except OSError:
        # No OLED. Treat it as a DummyHAT
        logging.debug("No OLED detected, We are retuning a Dummy HAT")
        return hats.DummyHAT

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

# the OLED is already set from the hat class test.  No need to retest.

def getDisplayClass(hatClass):
    logging.debug("Entering get Display Class")
    if hatClass != hats.DummyHAT and hatClass !=0:
        return displays.OLED
    else:
        logging.info("No OLED detected")
        return displays.DummyDisplay





@click.command()
@click.option('-v', '--verbose', is_flag=True, default=True)

def main(verbose):

    global hatClass
    global progress_file

    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
         logging.basicConfig(level=logging.DEBUG)

    if not os.path.exists("/usr/local/connectbox/wificonf.txt"):
        f = open("/usr/local/connectbox/wificonf.txt", "w")
        f.write("AccessPointIF=\n")
        f.write("ClientIF=\n")
        f.write("#####END######")
        f.close()
        logging.info("wrote temp wificonf.txt file out\g\g\g")

#Initialize the Global Variables

    while not ( os.path.exists( progress_file )):
      logging.info("waiting\g\g")
      time.sleep(5)	#we wait till we have a progress file
    time.sleep(2)	#make sure its filled 
    f = open(progress_file, "r")
    a = f.read()
    while  (a == "fdisk_done" or a =='resize_done'):
        f.close()
        time.sleep(10)
        f = open(progress_file, "r")
        a = f.read()
#  we wait because we need the disk resize to finishe
    f.close()
    print("into global inits")
# Use BCM pin numbering scheme for compatibility with CM4 and use Board compatability for NEO
    globals.init()
    if globals.device_type == "NEO":
         GPIO.setmode(GPIO.BOARD)
    elif globals.device_type == "OZ2":
         import orangepi.zero2
         GPIO.setmode(orangepi.zero2.BOARD)
    else:
         GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

# Go find the netowrk interfaces and seteup the wans
#    if getNetworkClass():        #sets up the AP and Client interfaces if it returns a 1 we need  to shutdown and start over
#        logging.info("getNetworkClass  asked for a reboot \g\g")
#        GPIO.cleanup()       # clean up GPIO on  reboot
#        os.sync()
#        time.sleep(2)
#        os.system("shutdown -r now")
#    else:
#      logging.debug("Finished netowrk class")
#     logging.info("Restart wlan0 and wlan1 interfaces")
#      os.system("ifconfig wlan0 up")
#      os.system("ifconfig wlan1 up")

#      logging.info("Finished display class")
#      logging.info("writing running to progress_file")
#    f = open(progress_file, "w")
#    f.write("running")
#   f.close()
#    os.sync()

    hatClass = getHATClass()
    displayClass =getDisplayClass(hatClass)

#    logging.debug("display Class is: "+str(displayClass))
#    logging.debug("finished display class starting main loop")
    try:
         hatClass(displayClass).mainLoop()
    except KeyboardInterrupt:
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit

   
if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
