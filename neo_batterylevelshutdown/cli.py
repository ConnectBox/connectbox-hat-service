# -*- coding: utf-8 -*-

"""Console script for neo_batterylevelshutdown."""

# Modified 11/05/19 JRA to detect no battery unit by asking the AXP209 whether battery exists
# AXP209 code comes from github.com/artizirk/python-axp209

import logging
import axp209
import click
import RPi.GPIO as GPIO  # pylint: disable=import-error
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
import neo_batterylevelshutdown.HAT_Utilities as utilities
import neo_batterylevelshutdown.globals as globals

def getHATClass():

    # As 6 is set to be a pulldown GPIO.setup(hats.BasePhysicalHAT.PA6, GPIO.IN resistor on system startup by the
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
    
    if globals.device_type == "NEO":
        io6 = 12  #PA6
        PA1 = 22  #PA1
        PA0 = 11  #PA0
        PG11 = 7  #PG11
    if globals.device_type == "CM":
        io6 = 31  #GPIO6/30   
        PA1 = 22  #GPIO25/41
        PG11 = 7  #GPIO4/54
        PA0 = 11  #GPIO17/50
    if globals.device_type == "PI":
        io6 = 12  #device is Pi GPIO18
        PA1 = 22  #GPIO25
        PG11 = 7  #GPIO4
        PA0 = 11  #GPIO17

    GPIO.setup(io6,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PG11,GPIO.IN, pull_up_down=GPIO.PUD_UP)
    if GPIO.input(io6) == GPIO.LOW:
        logging.info("NEO HAT not detected")
        return hats.DummyHAT

    try:
        axp = axp209.AXP209(globals.port)
        battexists = axp.battery_exists
        axp.close()
        # AXP209 found... we have HAT from Q3Y2018 or later
        # Test PA1... 
        #    HIGH => Q3Y2018 == HAT 4.6.7
        #    LOW =>          == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; HAT 7
        # Test PG11...
        #    HIGH => Q4Y2018 == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6
        #    LOW  => Q3Y2021 == HAT 7 
    
        GPIO.setup(PA1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if GPIO.input(PA1) == GPIO.LOW:
            if battexists:
                if (GPIO.input(PG11) == GPIO.HIGH) or (globals.device_type == "CM"):
                    logging.info("Q4Y2018 HAT Detected") 
                    return hats.q4y2018HAT
                else:
                    logging.info("Q3Y2021 HAT Detected")
                    return hats.q3y2021HAT
        # we have a non-battery HAT... we call all non-battery HATS "Q42019"
        #   Note that if we really want to use features of HAT 7 in a non-battery
        #    version, we will need to expand this search tree and create yet anotheer
        #    hat class.               
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

def call_battery():
    page_battery.PageBattery(self.display_device, self.axp)
    return

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
    globals.init()
    hatClass = getHATClass()
    displayClass = getDisplayClass()


    # displayClass = displays.OLEDA   #temp overwrite for debug - putting the overwrite here worked...
    # test to see if hatClass is hats.q1y2018HAT (no AXP209) but OLED present... 
    #  which would be a Q4Y2019HAT
    if ((hatClass == hats.q4y2019HAT) and (displayClass == displays.OLED)):
        displayClass = displays.OLEDA

    signal.signal(signal.SIGUSR1, call_battery)     #This outputs the battery voltage to a file
         
    logging.info("starting main loop")
    try:
        hatClass(displayClass).mainLoop()
    except KeyboardInterrupt:
        GPIO.cleanup()       # clean up GPIO on CTRL+C exit
    GPIO.cleanup()           # clean up GPIO on normal exit


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
