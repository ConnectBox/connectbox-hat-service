# -*- coding: utf-8 -*-

"""Console script for neo_batterylevelshutdown."""

# Modified 11/05/19 JRA to detect no battery unit by asking the AXP209 whether battery exists

import logging
import axp209
import click
import RPi.GPIO as GPIO  # pylint: disable=import-error
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
import neo_batterylevelshutdown.HAT_Utilities as utilities


def getHATClass():

    # As PA6 is set to be a pulldown GPIO.setup(hats.BasePhysicalHAT.PA6, GPIO.IN resistor on system startup by the
    #  pa6-pulldown.service, and the HAT sets PA6 HIGH, so we check the
    #  value of PA6, knowing non-HAT NEOs will read LOW.
    #
    # We assume the HAT is not present if we're unable to setup the pin
    #  or read from it. That's the safe option and means that we won't
    #  immediately shutdown devices that don't have a HAT if we've incorrect
    #  detected the presence of a HAT
    try:
        # See if we can find an OLED
        x = utilities.get_device()
    except OSError:
        # No OLED. This is a standard Axp209 HAT
        logging.info("No OLED detected")
        return hats.DummyHAT
    device_type = "NEO"
    io6 = 12    #PA6
    with open("/proc/cpuinfo", encoding = 'utf8')as f:
        filx = f.read()
        if ("Raspberry" in filx):
            if ("Compute Module" in filx):
                device_type = "CM"
                io6 = 31    #GPIO6/30            
            else:           #all other Raspberry Pi version other than compute modules
                device_type = "PI"
                io6 = 12    #device is Pi GPIO18
    f.close()

    GPIO.setup(io6,GPIO.INPUT)
    if GPIO.input(io6) == GPIO.LOW:
        logging.info("NEO HAT not detected")
        return hats.DummyHAT

    try:
        axp = axp209.AXP209()
        battexists = axp.battery_exists
        axp.close()
        # AXP209 found... we have HAT from Q3Y2018 or later
        # Test PA1... LOW => Q4Y2018; HIGH => Q3Y2018
        if (device_type == "NEO"):
            PA1 = 22    #PA1
        elif (device_type == "CM"):
            PA1 = 22    #GPIO25/41
        else:
            PA1 = 22    #GPIO25
        GPIO.setup(PA1, GPIO.IN)
        if GPIO.input(PA1) == GPIO.LOW:
            if battexists:
                logging.info("Q4Y2018 HAT Detected") 
                return hats.q4y2018HAT
            else:
                logging.info("Q42019 HAT Detected")
                return hats.q4y2019HAT

        logging.info("Q3Y2018 HAT Detected")
        return hats.q3y2018HAT
    except OSError:
        # There is no AXP209 on the Q12018 HAT
        logging.info("Q1Y2018 HAT Detected")
        return hats.q1y2018HAT
    except KeyboardInterrupt:
        pass

    return hats.DummyHAT   


def getDisplayClass():
    try:
        # See if we can find an OLED
        utilities.get_device()
        logging.info("Found OLED")
        return displays.OLED
    except OSError:
        # No OLED. This is a standard Axp209 HAT
        logging.info("No OLED detected")
        return displays.DummyDisplay


@click.command()
@click.option('-v', '--verbose', is_flag=True, default=False)
def main(verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(22, GPIO.IN,pull_up_down=GPIO.PUD_DOWN)  #for CM no pin is connected see it as low.
    hatClass = getHATClass()
    displayClass = getDisplayClass()
    # displayClass = displays.OLEDA   #temp overwrite for debug - putting the overwrite here worked...
    # test to see if hatClass is hats.q1y2018HAT (no AXP209) but OLED present... 
    #  which would be a Q4Y2019HAT
    if ((hatClass == hats.q4y2019HAT) and (displayClass == displays.OLED)):
        displayClass = displays.OLEDA
         
    logging.info("starting main loop")
    try:
        hatClass(displayClass).mainLoop()
    except KeyboardInterrupt:
        GPIO.cleanup()       # clean up GPIO on CTRL+C exit
    GPIO.cleanup()           # clean up GPIO on normal exit


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
