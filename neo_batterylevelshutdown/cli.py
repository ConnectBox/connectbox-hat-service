# -*- coding: utf-8 -*-

"""Console script for neo_batterylevelshutdown."""

# Modified 11/05/19 JRA to detect no battery unit by asking the AXP209 whether battery exists

import logging
import axp209
import click
import RPi.GPIO as GPIO  # pylint: disable=import-error
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
from .HAT_Utilities import get_device


def getHATClass():
    GPIO.setup(hats.BasePhysicalHAT.PA6, GPIO.IN)
    # As PA6 is set to be a pulldown resistor on system startup by the
    #  pa6-pulldown.service, and the HAT sets PA6 HIGH, so we check the
    #  value of PA6, knowing non-HAT NEOs will read LOW.
    #
    # We assume the HAT is not present if we're unable to setup the pin
    #  or read from it. That's the safe option and means that we won't
    #  immediately shutdown devices that don't have a HAT if we've incorrect
    #  detected the presence of a HAT
    if GPIO.input(hats.BasePhysicalHAT.PA6) == GPIO.LOW:
        logging.info("NEO HAT not detected")
        return hats.DummyHAT

    try:
        axp = axp209.AXP209()
        battexists = axp.battery_exists
        axp.close()
        # AXP209 found... we have HAT from Q3Y2018 or later
        # Test PA1... LOW => Q4Y2018; HIGH => Q3Y2018
        GPIO.setup(hats.q3y2018HAT.PA1, GPIO.IN)
        if GPIO.input(hats.q3y2018HAT.PA1) == GPIO.LOW:
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
        get_device()
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
    hatClass = getHATClass()
    displayClass = getDisplayClass()
#    displayClass = displays.OLEDA   #temp overwrite for debug - putting the overwrite here worked...
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
