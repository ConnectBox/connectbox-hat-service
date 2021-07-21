# -*- coding: utf-8 -*-

# hats.py
# Modified 10/17/19 by JRA to add new class q4y2019HAT (HAT 5.0.9 board with OLED but no AXP209) ie, the NoBatt version

from contextlib import contextmanager
import logging
import os
import os.path

import sys
import time
from axp209 import AXP209, AXP209_ADDRESS
import RPi.GPIO as GPIO  # pylint: disable=import-error
from .buttons import BUTTONS
global device_type
global PIN_LED


@contextmanager
def min_execution_time(min_time_secs):
    """
    Runs the logic within the context handler for at least min_time_secs

    This function will sleep in order to pad out the execution time if the
    logic within the context handler finishes early
    """
    start_time = time.monotonic()
    yield
    duration = time.monotonic() - start_time
    # If the function has run over the min execution time, don't sleep
    period = max(0, min_time_secs - duration)
    logging.debug("sleeping for %.2f secs to guarantee min exec time", period)
    time.sleep(period)


class BasePhysicalHAT:
    
    LED_CYCLE_TIME_SECS = 5

    # pylint: disable=unused-argument
    # This is a standard interface - it's ok not to use
    def __init__(self, displayClass):

        with open("/proc/cpuinfo", encoding = 'utf8')as f:
            filx = f.read()
            device_type = "NEO"
            if ("Raspberry" in filx):
                if ("Compute Module" in filx):
                    device_type = "CM"
                else:           #all other Raspberry Pi version other than compute modules
                    device_type = "PI"
        f.close()
    
        if (device_type == "NEO"):
            PIN_LED = PA6 = GPIO18 = 12 
        elif (device_type == "CM"):
            PIN_LED = GPIO6 = 31
        else:
            PIN_LED = GPIO18 = 12
            GPIO.setup(self.PIN_LED, GPIO.OUT)
            # All HATs should turn on their LED on startup. Doing it in the base
            #  class constructor allows us the main loop to focus on transitions
            #  and not worry about initial state (and thus be simpler)
            self.solidLED()

    @classmethod
    def shutdownDevice(cls):
        # Turn off the LED, as some people associate that with wifi being
        #  active (the HAT can stay powered after shutdown under some
        #  circumstances)
        GPIO.output(cls.PIN_LED, GPIO.HIGH)
        logging.info("Exiting for Shutdown")
        os.system("shutdown now")

    def shutdownDeviceCallback(self, channel):
        logging.debug("Triggering device shutdown based on edge detection "
                      "of GPIO %s.", channel)
        self.shutdownDevice()

    def blinkLED(self, times, flashDelay=0.3):
        for _ in range(0, times):
            GPIO.output(self.PIN_LED, GPIO.HIGH)
            time.sleep(flashDelay)
            GPIO.output(self.PIN_LED, GPIO.LOW)
            time.sleep(flashDelay)

    def solidLED(self):
        GPIO.output(self.PIN_LED, GPIO.LOW)


class DummyHAT:

    def __init__(self, displayClass):
        pass

    # pylint: disable=no-self-use
    # This is a standard interface - it's ok not to use self for a dummy impl
    def mainLoop(self):
        logging.info("There is no HAT, so there's nothing to do")


class q1y2018HAT(BasePhysicalHAT):

    # Pin numbers from https://github.com/auto3000/RPi.GPIO_NP
    PIN_VOLT_3_0 = PG6 = 8
    PIN_VOLT_3_45 = PG7 = 10
    PIN_VOLT_3_71 = PG8 = 16
    PIN_VOLT_3_84 = PG9 = 18

    def __init__(self, displayClass):
        logging.info("Initializing Pins")
        GPIO.setup(self.PIN_VOLT_3_0, GPIO.IN)
        GPIO.setup(self.PIN_VOLT_3_45, GPIO.IN)
        GPIO.setup(self.PIN_VOLT_3_71, GPIO.IN)
        GPIO.setup(self.PIN_VOLT_3_84, GPIO.IN)
        logging.info("Pin initialization complete")
        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors
        super().__init__(displayClass)
        # The circuitry on the HAT triggers a shutdown of the 5V converter
        #  once battery voltage goes below 3.0V. It gives an 8 second grace
        #  period before yanking the power, so if we have a falling edge on
        #  PIN_VOLT_3_0, then we're about to get the power yanked so attempt
        #  a graceful shutdown immediately.
        GPIO.add_event_detect(self.PIN_VOLT_3_0, GPIO.FALLING,
                              callback=self.shutdownDeviceCallback)
        # We cannot perform edge detection on PG7, PG8 or PG9 because there
        #  is no hardware hysteresis built into those level detectors, so when
        #  charging, the charger chip causes edge transitions (mostly rising
        #  but there are also some falling) at a rate of tens per second which
        #  means the software (and thus the board) is consuming lots of CPU
        #  and thus the charge rate is slower.

    def mainLoop(self):
        """
        monitors battery voltage and shuts down the device when levels are low
        """
        logging.info("Starting Monitoring")
        while True:
            with min_execution_time(min_time_secs=self.LED_CYCLE_TIME_SECS):
                if GPIO.input(self.PIN_VOLT_3_84):
                    logging.debug("Battery voltage > 3.84V i.e. > ~63%")
                    self.solidLED()
                    continue

                if GPIO.input(self.PIN_VOLT_3_71):
                    logging.debug("Battery voltage 3.71-3.84V i.e. ~33-63%")
                    self.blinkLED(times=1)
                    continue

                if GPIO.input(self.PIN_VOLT_3_45):
                    logging.debug("Battery voltage 3.45-3.71V i.e. ~3-33%")
                    # Voltage above 3.45V
                    self.blinkLED(times=2)
                    continue

                # If we're here, we can assume that PIN_VOLT_3_0 is high,
                #  otherwise we'd have triggered the falling edge detection
                #  on that pin, and we'd be in the process of shutting down
                #  courtesy of the callback.
                logging.info("Battery voltage < 3.45V i.e. < ~3%")
                self.blinkLED(times=3)


class Axp209HAT(BasePhysicalHAT):
    SHUTDOWN_WARNING_PERIOD_SECS = 60
    BATTERY_CHECK_FREQUENCY_SECS = 30
    MIN_BATTERY_THRESHOLD_PERC_SOLID = 63  # Parity with PIN_VOLT_3_84
    MIN_BATTERY_THRESHOLD_PERC_SINGLE_FLASH = 33  # Parity with PIN_VOLT_3_71
    MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH = 3  # Parity with PIN_VOLT_3_45
    BATTERY_WARNING_THRESHOLD_PERC = MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH
    BATTERY_SHUTDOWN_THRESHOLD_PERC = 1
    DISPLAY_TIMEOUT_SECS = 20
    # possibly should be moved elsewhere



    def __init__(self, displayClass):
        self.axp = AXP209()
        self.display = displayClass(self)
        self.buttons = BUTTONS(self, self.display)
        # Blank the screen 3 seconds after showing the logo - that's long
        #  enough. While displayPowerOffTime is read and written from both
        #  callback threads and the main loop, there's no TOCTOU race
        #  condition because we're only ever setting an absolute value rather
        #  than incrementing i.e. we're not referencing the old value
        self.displayPowerOffTime = time.time() + 3
        # If we have a battery, perform a level check at our first chance but
        #  if we don't, never schedule the battery check (this assumes that
        #  the battery will never be plugged in after startup, which is a
        #  reasonable assumption for non-development situations)
        if self.axp.battery_exists:
            self.nextBatteryCheckTime = 0
        else:
            # Never schedule it...
            self.nextBatteryCheckTime = sys.maxsize

        # Clear all IRQ Enable Control Registers. We may subsequently
        #  enable interrupts on certain actions below, but let's start
        #  with a known state for all registers.
        for ec_reg in (0x40, 0x41, 0x42, 0x43, 0x44):
            self.axp.bus.write_byte_data(AXP209_ADDRESS, ec_reg, 0x00)

        # Now all interrupts are disabled, clear the previous state
        self.clearAllPreviousInterrupts()

        # shutdown delay time to 3 secs (they delay before axp209 yanks power
        #  when it determines a shutdown is required) (default is 2 sec)
        hexval = self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x32)
        hexval = hexval | 0x03
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x32, hexval)
        # Set LEVEL2 voltage i.e. 3.0V
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x3B, 0x18)

        super().__init__(displayClass)


    def batteryLevelAbovePercent(self, level):
        # Battery guage of -1 means that the battery is not attached.
        # Given that amounts to infinite power because a charger is
        #  attached, or the device has found a mysterious alternative
        #  power source, let's say that the level is always above if
        #  we have a negative battery_gauge
        try:
            logging.debug("Battery Level: %s%%", self.axp.battery_gauge)
            gaugelevel = self.axp.battery_gauge
        except OSError:
            logging.error("Unable to read from AXP")
            gaugelevel = -1

        return gaugelevel < 0 or \
            gaugelevel > level

    def updateLEDState(self):
        if self.batteryLevelAbovePercent(
                self.MIN_BATTERY_THRESHOLD_PERC_SOLID):
            self.solidLED()
            return

        if self.batteryLevelAbovePercent(
                self.MIN_BATTERY_THRESHOLD_PERC_SINGLE_FLASH):
            self.blinkLED(times=1)
            return

        if self.batteryLevelAbovePercent(
                self.MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH):
            self.blinkLED(times=2)
            return

        # If we're here, we're below the double flash threshold and haven't
        #  yet been shutdown, so flash three times
        self.blinkLED(times=3)



    def clearAllPreviousInterrupts(self):
        """
        Reset interrupt state by writing a 1 to all bits of the state regs

        From the AXP209 datasheet:
        When certain events occur, AXP209 will inform the Host by pulling down
        the IRQ interrupt line, and the interrupt state will be stored in
        interrupt state registers (See registers REG48H, REG49H, REG4AH, REG4BH
        and REG4CH). The interrupt can be cleared by writing 1 to corresponding
        state register bit.

        Note that 0x4B is the only one that's enabled at this stage, but let's
        be thorough so that we don't need to change this if we start using the
        others.
        """
        # (IRQ status register 1-5)
        for stat_reg in (0x48, 0x49, 0x4A, 0x4B, 0x4C):
            self.axp.bus.write_byte_data(AXP209_ADDRESS, stat_reg, 0xFF)
        logging.debug("IRQ records cleared")

    def mainLoop(self):
        while True:
            with min_execution_time(min_time_secs=self.LED_CYCLE_TIME_SECS):
                # Perhaps power off the display
                if time.time() > self.displayPowerOffTime:
                    self.display.powerOffDisplay()

                # Check battery and possibly shutdown or show low battery page
                # Do this less frequently than updating LEDs. We could do
                #  these checks more frequently if we wanted to - the battery
                #  impact is probably minimal but that would mean we need to
                #  check for whether the battery is connected on each loop so
                #  readability doesn't necessarily improve
                if time.time() > self.nextBatteryCheckTime:
                    if not self.batteryLevelAbovePercent(
                            self.BATTERY_SHUTDOWN_THRESHOLD_PERC):
                        self.shutdownDevice()

                    if self.batteryLevelAbovePercent(
                            self.BATTERY_WARNING_THRESHOLD_PERC):
                        logging.debug("Battery above warning level")
                        # Hide the low battery warning, if we're currently
                        #  showing it
                        self.display.hideLowBatteryWarning()
                    else:
                        logging.debug("Battery below warning level")
                        # show (or keep showing) the low battery warning page
                        self.display.showLowBatteryWarning()
                        # Don't blank the display while we're in the
                        #  warning period so the low battery warning shows
                        #  to the end
                        self.displayPowerOffTime = sys.maxsize

                    self.nextBatteryCheckTime = \
                        time.time() + self.BATTERY_CHECK_FREQUENCY_SECS

                # Give a rough idea of battery capacity based on the LEDs
                self.updateLEDState()


class q3y2018HAT(Axp209HAT):

       
    def __init__(self, displayClass):
        with open("/proc/cpuinfo", encoding = 'utf8') as f:
            device_type = "NEO"
            filx = f.read()
            if ("Raspberry" in filx):
                if ("Compute Module" in filx):
                    device_type = "CM"
                else:           #all other Raspberry Pi version other than compute modules
                    device_type = "PI"
        f.close()   
        
        if (device_type == "NEO"):
            PIN_L_BUTTON = PG6 = 8 
            PIN_R_BUTTON = PG7 = 10 
            PIN_AXP_INTERRUPT_LINE = PG8 = 16
            USABLE_BUTTONS = [PIN_L_BUTTON, PIN_R_BUTTON]  # Used in the checkPressTime method
        elif (device_type =="CM"):
            PIN_L_BUTTON = PG6 = 5 #GPIO3/56  
            PIN_R_BUTTON = PG7 = 7 #GPIO4/54  
            PIN_AXP_INTERRUPT_LINE = PG8 = 10 #GPIO15/51
            USABLE_BUTTONS = [PIN_L_BUTTON, PIN_R_BUTTON]  # Used in the checkPressTime method
        else:                   #device type is Pi
            PIN_L_BUTTON = PG6 = 8 #GPIO 14
            PIN_R_BUTTON = PG7 = 10 #GPIO 15
            PIN_AXP_INTERRUPT_LIINE = PG8 = 16 #GPIO23

        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_M_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors
        super().__init__(displayClass)
        GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_M_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=self.powerOffDisplay,
                              bouncetime=125)

    def powerOffDisplay(self, channel):
        """Turn off the display"""
        logging.debug("Processing press on GPIO %s (poweroff).", channel)
        self.display.powerOffDisplay()
        # The display is already off... no need to set the power off time
        #  like we do in other callbacks


class q4y2018HAT(Axp209HAT):

    # Q4Y2018 - AXP209/OLED (Anker) Unit run specific pins
    # Pin numbers from https://github.com/auto3000/RPi.GPIO_NP

        
    def __init__(self, displayClass):
        with open("/proc/cpuinfo", encoding = 'utf8') as f:
            device_type = "NEO"
            filx = f.read()
            if ("Raspberry" in filx):
                if ("Compute Module" in filx):
                    device_type = "CM"
                else:           #all other Raspberry Pi version other than compute modules
                    device_type = "PI"
        f.close()   
        
        if (device_type == "NEO"):
            PIN_L_BUTTON = PG6 = 8 
            PIN_R_BUTTON = PG7 = 10 
            PIN_AXP_INTERRUPT_LINE = PG8 = 16
            USABLE_BUTTONS = [PIN_L_BUTTON, PIN_R_BUTTON]  # Used in the checkPressTime method
        elif (device_type =="CM"):
            PIN_L_BUTTON = PG6 = 5 #GPIO3/56  
            PIN_R_BUTTON = PG7 = 7 #GPIO4/54  
            PIN_AXP_INTERRUPT_LINE = PG8 = 10 #GPIO15/51
            USABLE_BUTTONS = [PIN_L_BUTTON, PIN_R_BUTTON]  # Used in the checkPressTime method
        else:                   #device type is Pi
            PIN_L_BUTTON = PG6 = 8 #GPIO 14
            PIN_R_BUTTON = PG7 = 10 #GPIO 15
            PIN_AXP_INTERRUPT_LIINE = PG8 = 16 #GPIO23    
    
        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_AXP_INTERRUPT_LINE, GPIO.IN)
        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors
        super().__init__(displayClass)
        GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)

        # We only enable interrupts on this HAT, rather than in the superclass
        #  because not all HATs with AXP209s have a line that we can use to
        #  detect the interrupt
        # Enable interrupts when battery goes below LEVEL2 or when
        #  N_OE (the power switch) goes high
        # Note that the axp209 will do a shutdown based on register 0x31[2:0]
        #  which is set to 2.9V by default, and as we're triggering a shutdown
        #  based on LEVEL2 that mechanism should never be necessary
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x43, 0x41)
        # We've masked all other interrupt sources for the AXP interrupt line
        #  so the desired action here is always to shutdown
        GPIO.add_event_detect(self.PIN_AXP_INTERRUPT_LINE, GPIO.FALLING,
                              callback=self.shutdownDeviceCallback)
                              

class q4y2019HAT(BasePhysicalHAT):

    # Q4Y2019 - nomenclature for a Q4Y2018 HAT without a battery
    #  This code a hack of copying Q4Y2018 code, parenting direct from BasePhysicalHAT and including
    #   the interrupt code. Also borrowed from the Axp209HAT class, all the display stuff
    # Pin numbers from https://github.com/auto3000/RPi.GPIO_NP

    
    def __init__(self, displayClass):
        with open("/proc/cpuinfo", encoding = 'utf8') as f:
            device_type = "NEO"
            filx = f.read()
            if ("Raspberry" in filx):
                if ("Compute Module" in filx):
                    device_type = "CM"
                else:           #all other Raspberry Pi version other than compute modules
                    device_type = "PI"
        f.close()   
        
        if (device_type == "NEO"):
            PIN_L_BUTTON = PG6 = 8 
            PIN_R_BUTTON = PG7 = 10 
            PIN_AXP_INTERRUPT_LINE = PG8 = 16
            USABLE_BUTTONS = [PIN_L_BUTTON, PIN_R_BUTTON]  # Used in the checkPressTime method
        elif (device_type =="CM"):
            PIN_L_BUTTON = PG6 = 5 #GPIO3/56  
            PIN_R_BUTTON = PG7 = 7 #GPIO4/54  
            PIN_AXP_INTERRUPT_LINE = PG8 = 10 #GPIO15/51
            USABLE_BUTTONS = [PIN_L_BUTTON, PIN_R_BUTTON]  # Used in the checkPressTime method
        else:                   #device type is Pi
            PIN_L_BUTTON = PG6 = 8 #GPIO 14
            PIN_R_BUTTON = PG7 = 10 #GPIO 15
            PIN_AXP_INTERRUPT_LIINE = PG8 = 16 #GPIO23
    
        # Next 3 lines from Axp209HAT class
        self.display = displayClass(self)   
        self.buttons = BUTTONS(self, self.display)
        self.displayPowerOffTime = time.time() + 3

        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_AXP_INTERRUPT_LINE, GPIO.IN)
        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors
        super().__init__(displayClass)
        GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        
        # For the Q4Y2019HAT, the power switch is tied to the IRQ line and so
        #   when moved to the OFF position, will pull the "AXP interrupt line"
        #   low, even though there is NO AXP209 present                      
        # The desired action here is always to shutdown
        GPIO.add_event_detect(self.PIN_AXP_INTERRUPT_LINE, GPIO.FALLING,
                              callback=self.shutdownDeviceCallback)
  
  
# from Axp209HAT...
    def mainLoop(self):
        while True:
            with min_execution_time(min_time_secs=self.LED_CYCLE_TIME_SECS):
                # Perhaps power off the display
                if time.time() > self.displayPowerOffTime:
                    self.display.powerOffDisplay()


                               
