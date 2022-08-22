# -*- coding: utf-8 -*-

# hats.py
# Modified 10/17/19 by JRA to add new class q4y2019HAT (HAT 5.0.9 board with OLED but no battery) ie, the NoBatt version
#  11/30/21 JRA - Q4Y2019 Hat class removed - no battery instance handled in battery pages

from contextlib import contextmanager
import logging
import os
import os.path
import io
import sys
import time

#JRA - 011322
#import smbus2

from axp209 import AXP209, AXP209_ADDRESS
import neo_batterylevelshutdown.globals as globals
import RPi.GPIO as GPIO  # pylint: disable=import-error
from .buttons import BUTTONS
import neo_batterylevelshutdown.multiBat_Utilities as mb_utilities
    
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
    time.sleep(period)


class BasePhysicalHAT:

    LED_CYCLE_TIME_SECS = 5

    # pylint: disable=unused-argument
    # This is a standard interface - it's ok not to use
    def __init__(self, displayClass):

        if globals.device_type == "NEO":
            self.PIN_LED = 12    # PA6
        if globals.device_type == "CM":
            self.PIN_LED = 6    # GPIO6
        if globals.device_type == "PI":
            self.PIN_LED = 6    # GPIO6


        GPIO.setup(self.PIN_LED, GPIO.OUT)
            # All HATs should turn on their LED on startup. Doing it in the base
            #  class constructor allows us the main loop to focus on transitions
            #  and not worry about initial state (and thus be simpler)
        self.solidLED()

#    @classmethod
    def shutdownDevice(self):
        # Turn off the LED, as some people associate that with wifi being
        #  active (the HAT can stay powered after shutdown under some
        #  circumstances)
        GPIO.output(self.PIN_LED, GPIO.HIGH)
        self.display.showPoweringOff()
        logging.info("Exiting for Shutdown")
        os.system("shutdown now")
        # Stick here to leave the showPoweringOff() display on to the end
        while True:
            pass

    def shutdownDeviceCallback(self, channel):
        logging.info("Triggering device shutdown based on edge detection "
                      "of GPIO %s.", channel)
        # do some verification that the IRQ is still low after 100 ms
        time.sleep(0.1)
        # if interrupt line is high, this was a false trigger... just return
        if GPIO.input(self.PIN_AXP_INTERRUPT_LINE):
            return   
        self.shutdownDevice()

    def handleOtgSelect(self, channel):
        logging.debug("OTG edge detected ")
        # OTG ONLY IMPLEMENTED FOR NEO HAT 7.0 ONLY! OTG can be used on a Pi4, PiZero or CM4
        # but also needs to have the correct drivers installed (dtoverlay=dwc2,dr_mode=(host, peripheral,otg)
        # and needs the proper module loaded either on the dtoverlay line, etc. but does not call this
        # interrupt handler.

        # On the Neo we have a signal to detect changes in OTG_ID signal. 
        # disable interrupt for a bit to find if the level on channel is HIGH or LOW
        #  and based on that, choose whether to enable or disable OTG service
        # Note that this is a specific case of OTG sense being on PA0... 
        #  If another implementation is made for NEO, this will need updating.
        #
        #  FUTURE: make this a general case handler for ANY channel on the NEO
        #
        # Register calculation from Allwinner_H3_Datasheet_v1.1.pdf page 316 ff
        #   Base address = 0x01c20800 ... PA0 is in bits 2:0 of offset 0x00
        # globals.otg =0 for off;  high to enable OTG and "none" for enabled inverted OTG 
        # and 'both' for always otg regardless of state
        if globals.otg=='0' or globals.otg == 0:
            retval = os.popen("grep "+globals.g_device).read()
            if retval != "":
                retval = os.popen('modprobe -r '+globals.g_device)     #make sure there is no g_device loaded by default.
            return
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c20800"      #set up to read the config value for PA0
            retval = os.popen(cmd).read()   # the stdout of the command
            init_val = int(retval.split(":")[1],16)     # The initial (integer) value of the register
            write_val = init_val & 0x77777770           # Mask to set the PA0 pin to INPUT
            cmd1 = cmd + " w " + hex(write_val)          # Form the command
            retval = os.popen(cmd1).read()                     # Write the register

            if globals.otg == "none":
                otg_xor = 1
            else:
                otg_xor = 0

            # we are now in input mode for the pin...
            if globals.otg == "both":
                otg_mode = True
                logging.debug("The OTG pin state dosn't matter were enabled in any case")
            else:
                if (globals.otg ^ otg_xor) == 0:
                    logging.debug("The OTG pin is LOW, so leaving OTG mode")
                    otg_mode = False
                else:
                    logging.debug("The OTG pin is HIGH, so entering OTG mode")
                    otg_mode = True

            # we are through with using the OTG pin as an input... put the register back as it was
            if (globals.device_type == "NEO"):
                cmd2 = cmd + " w " + hex(init_val)      #form command to write the orginal value back
                retval = os.popen(cmd2).read()          # the stdout of the command

            # Now we have determined the OTG request, so do the requested work
            if otg_mode == True:
                logging.debug("in OTG set")
                retval = os.popen("grep "+globals.g_device+" /proc/modules").read()
                if retval == "":
                    # module was not loaded we couldn't find it at least.  So lets get to loading
                    retval = os.popen("modprobe "+globals.g_device+" "+globals.enable_mass_storage).read()
                    if retval.find("FATAL") <= 0:
                        logging.info("failed to load the driver "+globals.g_device+" "+globals.enable_mass_storage)
                        return
                    else:
                        retval = os.popen("systemctl daemon-reload").read()
                        if globals.g_device == 'g_serial':
                            retval = os.popen("systemctl restart serial-getty@ttyGS0.service").read()
                            if retval != "":
                                logging.info("load of g_serial serial-getty@ttyGS0.service failed")
                    #######################################################################
                    #What other service needs to be started or checked due to loading a module
                    #We need to figure that out?
                    #######################################################################
                    return
                else:
                    # module was already loaded so wnat do we need to do?
                    if globals.g_device == 'g_serial':
                        retval = os.popen("systemctl status service-getty@ttyGS).service").read()
                        if retval.find("active (running)") <= 0:
                            retval = os.popen("systemctl restart serial-getty@ttyGS0.service").read()
                            if retval != "":
                                logging.info("load of g_serial serial-getty@ttyGS0.service failed")
                    #######################################################################
                    #What other service needs to be started or checked due to loading a module
                    #We need to figure that out?
                    #######################################################################
                    return
            else:
                logging.debug("not OTG set")
                retval = os.popen("grep "+globals.g_device+" /proc/modules").read()
                if retval.find("filename"):
                    retval = os.popen("modprobe -r "+globals.g_device).read()
                    if retval.find("FATAL"):
                        logging.debug("modprobe operation to remove "+globals.g_device+" failed!")
        return
    # End of the OTG interrupt handler.......


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
        logging.info("There is no HAT, so there's nothing to do using DummyHat")


class q1y2018HAT(BasePhysicalHAT):
    # The circuitry on the Q1Y2018 HAT had voltage comparators to determine
    # battery voltage. All later HATs use the AXP209 for finding voltages
    # This HAT was ONLY made for NEO 


    def __init__(self, displayClass):

        # The circuitry on the HAT triggers a shutdown of the 5V converter
        #  once battery voltage goes below 3.0V. It gives an 8 second grace
        #  period before yanking the power, so if we have a falling edge on
        #  PIN_VOLT_3_0, then we're about to get the power yanked so attempt
        #  a graceful shutdown immediately.

        if globals.device_type == "NEO":
        # Pin numbers specified in BCM format
            PIN_VOLT_3_0 =  8       # PG6 
            PIN_VOLT_3_45 = 10      # PG7
            PIN_VOLT_3_71 = 16      # PG8
            PIN_VOLT_3_84 = 18      # PG9
            logging.info("Found Q1Y2018HAY for neo")
        else:
            # Pin numbers specified in BCM format
            PIN_VOLT_3_0 =  14      # PG6 
            PIN_VOLT_3_45 = 15      # PG7
            PIN_VOLT_3_71 = 23      # PG8
            PIN_VOLT_3_84 = 24      # PG9
            logging.info("Found Q1Y2018HAY for Pi")


        if (globals.device_type == "NEO"):
            logging.info("Initializing Pins")
            GPIO.setup(self.PIN_VOLT_3_0, GPIO.IN)
            GPIO.setup(self.PIN_VOLT_3_45, GPIO.IN)
            GPIO.setup(self.PIN_VOLT_3_71, GPIO.IN)
            GPIO.setup(self.PIN_VOLT_3_84, GPIO.IN)

            # Run parent constructors before adding event detection
            #  as some callbacks require objects only initialised
            #  in parent constructors
            super().__init__(displayClass)
            GPIO.add_event_detect(self.PIN_VOLT_3_0, GPIO.FALLING, \
                              callback=self.shutdownDeviceCallback)
            # We cannot perform edge detection on PG7, PG8 or PG9 because there
            #  is no hardware hysteresis built into those level detectors, so when
            #  charging, the charger chip causes edge transitions (mostly rising
            #  but there are also some falling) at a rate of tens per second which
            #  means the software (and thus the board) is consuming lots of CPU
            #  and thus the charge rate is slower.

    def powerOffDisplay(self, channel):
        """Turn off the display"""
        logging.debug("Processing press on GPIO %s (poweroff).", channel)
        self.display.powerOffDisplay()
        # The display is already off... no need to set the power off time
        #  like we do in other callbacks


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
    MIN_BATTERY_THRESHOLD_PERC_SOLID = 63         # Parity with PIN_VOLT_3_84
    MIN_BATTERY_THRESHOLD_PERC_SINGLE_FLASH = 33  # Parity with PIN_VOLT_3_71
    MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH = 3   # Parity with PIN_VOLT_3_45
    BATTERY_WARNING_THRESHOLD_PERC = MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH
    BATTERY_WARNING_VOLTAGE = 3400                # CM4 warning voltage (mV)
    BATTERY_SHUTDOWN_VOLTAGE = 3000               # CM4 shutdown voltage (mV)
    BATTERY_SHUTDOWN_THRESHOLD_PERC = 1
    DISPLAY_TIMEOUT_SECS = 120
    # possibly should be moved elsewhere


    def __init__(self, displayClass):

        self.axp = AXP209(globals.port)         # Pass the port number to get the right device
        self.display = displayClass(self)
        self.buttons = BUTTONS(self, self.display)
        # Blank the screen 3 seconds after showing the logo - that's long
        #  enough. While displayPowerOffTime is read and written from both
        #  callback threads and the main loop, there's no TOCTOU race
        #  condition because we're only ever setting an absolute value rather
        #  than incrementing i.e. we're not referencing the old value
        self.displayPowerOffTime = time.time() + 3
        # establish self.nextBatteryChecktime so that if
        #  we have a battery, perform a level check at our first chance 
        #  (removed assumption that battery will not be added or removed in
        #   real use case)
        self.nextBatteryCheckTime = 0
        
        # Clear all IRQ Enable Control Registers. We may subsequently
        #  enable interrupts on certain actions below, but let's start
        #  with a known state for all registers.
        for ec_reg in (0x40, 0x41, 0x42, 0x43, 0x44):
            self.axp.bus.write_byte_data(AXP209_ADDRESS, ec_reg, 0x00)

        # Write the charge control 1 - limit/ current control register 
        #  (Vtarget = 4.1 volts, end charging when below 10% of set charge current, 
        #   charge current = 1200 mA )
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x33, 0xC9)    # V(trgt) = 4.2V (was 0x89... 4.1V)

        # Enable AC_IN current and voltage ADCs (also ADCs for Battery voltage, Battery current, 
        #  and APS voltage.)
        #  note: APS monitors the IPSOUT voltage and shuts down system if < 2.9 volts.
        #        also, the Battery Temp Sense (TS) ADC is left enabled because disabling it
        #        results in a battery error warning LED (?)
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x82, 0xF3)

        # Change Voff voltage level (level of IPS_OUT below which causes AXP209 to shutdown)
        #  to 3.0V. 
        self.axp.bus.write_byte_data(AXP209_ADDRESS,0x31,0x04)  # AXP209 trigger shutdown at Vbatt = 3.0V


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
            gaugelevel = self.axp.battery_gauge
        except OSError:
            logging.error("Unable to read from AXP")
            gaugelevel = -1

        return gaugelevel < 0 or \
            gaugelevel > level

    def batteryLevelAboveVoltage(self, level):      # level in mV
        try:
            voltagelevel = self.axp.battery_voltage  # returns mV
        except OSError:
            logging.error("Unable to read from AXP")
            voltagelevel = -1

        return voltagelevel < 0 or \
            voltagelevel > level


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
            # The following ensures that the while loop only executes once every 
            #  LED_CYCLE_TIME_SECS...
            with min_execution_time(min_time_secs=self.LED_CYCLE_TIME_SECS):
                # Perhaps power off the display
                if time.time() > self.displayPowerOffTime:
                    self.display.powerOffDisplay()


    # Read the battery in use number from ATTiny, read the voltage from AXP209, re-read the battery number
    #  (make sure battery didn't change), write the battery voltage/16 to ATTiny
    #  and to local array bat_voltage[]
    # With ATTiny rev 0x19, we don't need to store battery voltages in 0x21-0x24
    #  but we will store there anyway for backwards compatibility
                result = batteryNumber = mb_utilities.i2c_read(0x31)
                if (result != -1):          # valid read of ATTiny so ATTiny handling battery switching
                    try:
                        batteryVoltage = int(self.axp.battery_voltage)
                    except:
                        batteryVoltage = 3100   # AXP209 i2c fails at 3100 mV    
                    wr_scaled = int(batteryVoltage/16)
                    if (wr_scaled > 0xFF):
                        wr_scaled = 0xFF
                    reread = mb_utilities.i2c_read(0x31)
                    if (batteryNumber == reread):
                        wr_result = mb_utilities.i2c_write(0x20+batteryNumber, wr_scaled)
                        # store unscaled voltage directly to array 
                        mb_utilities.v_update_array(batteryNumber,batteryVoltage) 


                else:       # no ATTiny, so CM4 handling battery selection
                    # code here to have CM4 check for which batteries are present and
                    #  which battery is in use; read the voltage of the battery and store
                    #  in the global array for use by the page_multi_bat.py code (and possibly others)
                    pass    # This is a stub for now    
 
    # Perhaps here we add a call to update the current page
    #  self.display.redrawCurrentPage()
    #   PERHAPS ADD TEST TO DO THIS ONLY FOR PAGES 0 -> 4
                #logging.info("... redraw current page")
                self.display.redrawCurrentPage()

                # Check battery and possibly shutdown or show low battery page
                # Do this less frequently than updating LEDs. We could do
                #  these checks more frequently if we wanted to - the battery
                #  impact is probably minimal but that would mean we need to
                #  check for whether the battery is connected on each loop so
                #  readability doesn't necessarily improve
                # (added test for battery exists for removable battery systems)
                try:
                    axp_there = self.axp.battery_exists
                except:
                    axp_there = False      # AXP209 i2c shutdown, likely Vbatt<3.1V
                # if axp_there == False, we will allow the AXP to do shutdown based on 
                #     V(level2) triggering the IRQ for power off
                #  otherwise, continue to monitor Vbatt from AXP209   
                if (time.time() > self.nextBatteryCheckTime) and (axp_there):
                    logging.info("BATTERY VOLTAGE CHECK BEGINS")
                    if not self.batteryLevelAboveVoltage(
                            self.BATTERY_SHUTDOWN_VOLTAGE):
                        logging.info("BATTERY_SHUTDOWN_VOLTAGE reached")
                        hexval = self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x32)
                        hexval = hexval | 0x80      # signal AXP209 to shutdown power
                        self.display.showPoweringOff()
                        logging.info("Exiting for Shutdown due to battery exhaustion")
                        time.sleep(5)       # show power down screen for 5 seconds
                        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x32, hexval)
                        while True:
                            pass        # stick here while irq is serviced


                    if self.batteryLevelAboveVoltage(
                            self.BATTERY_WARNING_VOLTAGE):
                        # Hide the low battery warning, if we're currently
                        #  showing it
                        self.display.hideLowBatteryWarning()
                    else:
                        logging.info("BATTERY_WARNING_VOLTAGE reached")
                         # show (or keep showing) the low battery warning page
                        self.display.showLowBatteryWarning()
                        # Don't blank the display while we're in the
                        #  warning period so the low battery warning shows
                        #  to the end
                        self.displayPowerOffTime = sys.maxsize
                        # we are near shutdown... force check every time around loop (5 sec)
                        self.BATTERY_CHECK_FREQUENCY_SECS = 4   

                    self.nextBatteryCheckTime = \
                        time.time() + self.BATTERY_CHECK_FREQUENCY_SECS

                    # Give a rough idea of battery capacity based on the LEDs
                    self.updateLEDState()

                    # Check to see if anyone changed the brand.txt file if so we need to reload
                    globals.init()


class q3y2018HAT(Axp209HAT): 

    # HAT 4.6.7 - This is ONLY a NEO HAT

    def __init__(self, displayClass):

        if globals.device_type == "NEO":
            self.PIN_L_BUTTON =   8             #  PA1
            self.PIN_R_BUTTON =   10            #  PG7
    #        self.PIN_AXP_INTERRUPT_LINE = 16
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2018HAT for neo")
        else:
            self.PIN_L_BUTTON =   14            #  PA1
            self.PIN_R_BUTTON =   15            #  PG7
    #        self.PIN_AXP_INTERRUPT_LINE = 23
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2018HAT for Pi")


        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
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

    def powerOffDisplay(self, channel):
        """Turn off the display"""
        logging.debug("Processing press on GPIO %s (poweroff).", channel)
        self.display.powerOffDisplay()
        # The display is already off... no need to set the power off time
        #  like we do in other callbacks


class q4y2018HAT(Axp209HAT):

    # The CM4 resolves to this HAT class

    # Q4Y2018 - AXP209/OLED (Anker) Unit run specific pins
    # All pin references are now BCM format

    def __init__(self, displayClass):

        if (globals.device_type == "NEO"):
            self.PIN_L_BUTTON = 8              # PG6
            self.PIN_R_BUTTON = 10              # PG7
            self.PIN_AXP_INTERRUPT_LINE = 16    # PG8
            self.PIN_OTG_SENSE = 11               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for neo")
        elif (globals.device_type =="CM"):
            self.PIN_L_BUTTON = 3               # GPIO3/56
            self.PIN_R_BUTTON = 4               # GPIO4/54
            self.PIN_AXP_INTERRUPT_LINE = 15    # GPIO15/51
            self.PIN_OTG_SENSE = 17               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for CM4")

        # We don't currently have a HAT for RPi... so we will get here if HAT wiring is same as CM4 for GPIO
        #  For the moment, we will assume a HAT with GPIO assignments the same as CM4
        else:                   #device type is Pi
            self.PIN_L_BUTTON = 3               # GPIO3
            self.PIN_R_BUTTON = 4               # GPIO4
            self.PIN_AXP_INTERRUPT_LIINE = 15   # GPIO15
            self.PIN_OTG_SENSE = 17               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for Pi")

        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_AXP_INTERRUPT_LINE, GPIO.IN)
        GPIO.setup(self.PIN_OTG_SENSE, GPIO.IN)
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
        GPIO.add_event_detect(self.PIN_OTG_SENSE, GPIO.BOTH,
                               callback=self.handleOtgSelect,
                               bouncetime=125)


        # We only enable interrupts on this HAT, rather than in the superclass
        #  because not all HATs with AXP209s have a line that we can use to
        #  detect the interrupt
        # Enable interrupts [ DEPRICATED -- when battery goes below LEVEL2] or when
        #  N_OE (the power switch) goes high
        # Note that the axp209 will do a shutdown based on register 0x31[2:0]
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x43, 0x40)
        # We've masked all other interrupt sources for the AXP interrupt line
        #  so the desired action here is always to shutdown
        GPIO.add_event_detect(self.PIN_AXP_INTERRUPT_LINE, GPIO.FALLING,
                              callback=self.shutdownDeviceCallback)
        self.handleOtgSelect(self.PIN_OTG_SENSE)



class q3y2021HAT(Axp209HAT):

    # Q3Y2021 - HAT 7.0.x - NEO ONLY

    def __init__(self, displayClass):

        if globals.device_type == "NEO":
            self.PIN_L_BUTTON = 8                 #PG6
            self.PIN_R_BUTTON = 10                #PG7
            self.PIN_AXP_INTERRUPT_LINE = 16      #PG8
            self.PIN_OTG_SENSE = 11               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2021HAT for neo")
        else:
            self.PIN_L_BUTTON = 14                #PG6
            self.PIN_R_BUTTON = 15                #PG7
            self.PIN_AXP_INTERRUPT_LINE = 23      #PG8
            self.PIN_OTG_SENSE = 17               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            loggitng.info("found q3y2021HAT for Pi")


        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_AXP_INTERRUPT_LINE, GPIO.IN)
        GPIO.setup(self.PIN_OTG_SENSE, GPIO.IN)
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
        GPIO.add_event_detect(self.PIN_OTG_SENSE, GPIO.BOTH,
                               callback=self.handleOtgSelect,
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
        self.handleOtgSelect(self.PIN_OTG_SENSE)
