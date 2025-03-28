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
import smbus2


# We import globals here so we can run globals.init() (establishing the processor type)
#  so we can choose the correct GPIO library

import neo_batterylevelshutdown.globals as globals
globals.init()
globals.sequence = 0


if globals.device_type == "RM3":
    import radxa.CM3
    import OPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "NEO":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "OZ2":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
    import orangepi.zero2
else:
    import RPi.GPIO as GPIO  # pylint: disable=import-error


# Having imported globals and run globals.init() (above) importing hats (and hats importing
#  buttons) means both of those have access to globals variables (specifically, globals.device_type)
#  at the top of the module... so they can make similar decisions as to which GPIO to import
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
import neo_batterylevelshutdown.HAT_Utilities as utilities

# Use BCM pin numbering scheme for compatibility with CM4 and use Board compatability for NEO


# Global definitions for this module
hatClass = 0
progress_file = "/usr/local/connectbox/expand_progress.txt"


def getHATClass():
    logging.info("Entering get Hat Class")
    # We assume the HAT is not present if we're unable to setup the pin
    #  or read from it. That's the safe option and means that we won't
    #  immediately shutdown devices that don't have a HAT if we've incorrect
    #  detected the presence of a HAT

    try:
        # See if we can find an OLED
        utilities.get_device()
    except OSError:
        # No OLED. Treat it as a DummyHAT
        logging.info("No OLED detected, We are retuning a Dummy HAT")
        return hats.DummyHAT


# Express all pin numbers in BCM nomenclature for compatibility with CM4
#  (which requires BCM)
# We will carry the original, NEO based names but use BCM pin numbers
#  Note that PA1 is used only for version testing in NEO, so for RPi (PI and CM4)
#   versions we specify an un-connected pin... GPIO25
#   PA0 only used on HAT7 for OTG sense... spec un-connected pin on others
#    (but PA0 not tested here... so we don't need to define here...)

# While we do pin assignments here we don't use PA0 and PA1 in this module (they are for ref)
    if globals.device_type == "RM3":
        PA6  = 31   # GPIO6 - Amber LED ... perhaps consider renaming (globally) PA6 -> AMBER ??
        PA1  = 22   # GPIO25 - unconnected
        PG11 = 7    # GPIO4  - PB2
#        PA0  = 11   # GPIO17 - unconnected
    if globals.device_type == "NEO":
        PA6 = 12    #PA6    Amber LED pin #
        PA1 = 22    #PA1    Test for HAT 4.6.7 (all other HATs have this pin unconnected) pin #
        PG11 = 7    #PG11   Test of HAT 7 pin #
#        PA0 = 11    #PA0    OTG sense (HAT7), not used on others pin #
    if globals.device_type == "CM":    # running as BCM (not BOARD)
        PA6 = 6     #GPIO6/30 - Amber LED
        PA1 = 25    #GPIO25/41 - unconnected
        PG11 = 4    #GPIO4/54   Actually GPIO4 is PB2 which will be HIGH on CM4 HAT
#        PA0 = 17    #GPIO17/50 - unconnected
    if globals.device_type == "PI":
        PA6 = 18    #device is Pi GPIO18
        PA1 = 23    #GPIO25
        PG11 = 4    #GPIO4
#        PA0 = 17    #GPIO17

    logging.info("passed GPIO no hat test looking for AXP209")

    # Test axp first... if we have an AXP then no need to test PA6
    # RETHINK THIS LOGIC TO AVOID TESTING GPIO PINS IF POSSIBLE
    try:
        axp = axp209.AXP209(globals.port)
    # moved the battexists = axp.battery_exists test to the individual battery display pages
        axp.close()
        # AXP209 found... we have HAT from Q3Y2018 or later
        # Test PA1...
        #    HIGH => Q3Y2018 == HAT 4.6.7
        #    LOW =>          == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; HAT 7; CM4; RM3
        # Test PG11...
        #    HIGH => Q4Y2018 == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; CM4
        #    LOW  => Q3Y2021 == HAT 7

    # if device_type is CM4 or RM3, and we have AXP209 (ie not bare board) then this
    #  is a q4y2018 hat class... we will assign that without GPIO tests of PA6 to avoid
    #  issues with possible false detection of PA6 state
        if globals.device_type == 'RM3' or globals.device_type == 'CM4':
            return hats.q4y2018HAT


        GPIO.setup(PA6,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(PG11,GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PA1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


        # all HATs have PA6 (Amber LED) connected HIGH, so if this is low, we have no HAT
        if GPIO.input(PA6) == GPIO.LOW:
            logging.info("NEO HAT not detected")
            return hats.DummyHAT


        if GPIO.input(PA1) == GPIO.LOW:
            if (GPIO.input(PG11) == GPIO.HIGH):
            # This would include CM4 HAT as "PG11" is assigned to GPIO4
            #  and that is wired to PB2 (normally HIGH)
                logging.info(" Q4Y2018 HAT Detected")
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
    logging.info("Entering get Display Class")
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

    logging.info("********* cli.py at main")

# Here we do the GPIO setmode based on board type
    GPIO.cleanup()              # remove associations
    GPIO.setwarnings(False)

    if globals.device_type == "RM3":
        GPIO.setmode(radxa.CM3.BOARD)
    elif globals.device_type == "NEO":
        GPIO.setmode(GPIO.BOARD)
    elif globals.device_type == "OZ2":
        GPIO.setmode(orangepi.zero2.BOARD)
    else:
        GPIO.setmode(GPIO.BCM)

    if not os.path.exists("/usr/local/connectbox/wificonf.txt"):
        f = open("/usr/local/connectbox/wificonf.txt", "w")
        f.write("AccessPointIF=\n")
        f.write("ClientIF=\n")
        f.write("#####END######")
        f.close()
        logging.info("wrote temp wificonf.txt file out")


    try:
        os.system("rm /tmp/creating_menus.txt")
    except:
        pass

#Initialize the Global Variables

    while not ( os.path.exists( progress_file )):
      logging.info("waiting")
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
#    print("into global inits")

# in getHATClass we do GPIO pin assignments
    hatClass = getHATClass()
    print("hatClass is: " + str(hatClass))
    displayClass =getDisplayClass(hatClass)
    print("DisplayClass is: " + str(displayClass))
#    logging.info("display Class is: "+str(displayClass))
#    logging.info("finished display class starting main loop")

    try:
        hatClass(displayClass).mainLoop()
    except KeyboardInterrupt:
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
