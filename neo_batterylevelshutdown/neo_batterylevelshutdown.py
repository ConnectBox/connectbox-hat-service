# -*- coding: utf-8 -*-

"""
===========================================
  blinkLED.py
  https://github.com/GeoDirk/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
===========================================
"""
import logging
import os
import time
import threading


PIN_LED = 6  # PA6 pin
PIN_VOLT_3_0 = 198  # PG6 pin - shutdown within 10 seconds
PIN_VOLT_3_2 = 199  # PG7 pin - above 3.2V
PIN_VOLT_3_4 = 200  # PG8 pin - above 3.4V
PIN_VOLT_3_6 = 201  # PG9 pin - above 3.6V
LED_FLASH_DELAY_SEC = 0.1
GPIO_EXPORT_FILE = "/sys/class/gpio/export"

PIN_HIGH = "1"
PIN_LOW = "0"

def setup_gpio_pin(pinNum, direction, resistor):
    """Setup the GPIO Pin for operation in the system OS"""
    if not os.path.isfile(GPIO_EXPORT_FILE):
        logging.warn("Unable to find GPIO export file: %s "
                     "Is GPIO_SYSFS active?", GPIO_EXPORT_FILE)
        return False

    # Has this pin been exported?
    pinPath = "/sys/class/gpio/gpio{}".format(pinNum)
    if not os.path.isfile(pinPath):
        try:
            # Export pin for access
            # with open(GPIO_EXPORT_FILE, "w") as f:
            #     f.write(str(pinNum))
            os.system("echo {} > /sys/class/gpio/export".format(pinNum))
            logging.info("GPIO pin %s Export Complete", pinNum)
            # Configure the pin direction
            with open(os.path.join(pinPath, "direction"), 'w') as f:
                f.write(direction)
            logging.info("GPIO pin %s Direction Complete", pinNum)
            # Configure the pull up (1) / pull down resistor (0)
            with open(os.path.join(pinPath, "active_low"), 'w') as f:
                f.write(str(resistor))
            logging.info("GPIO pin %s active_low Complete", pinNum)
        except OSError:
            logging.warn("Error setting up GPIO pin %s", pinNum)
            return False

    return True


def blink_LEDxTimes(pinNum, times):
    """Blink the LED a certain number of times"""
    try:
        for _ in range(0, times):
            with open("/sys/class/gpio/gpio{}/value".format(pinNum), "w") as pin:
                pin.write(PIN_HIGH)
            time.sleep(LED_FLASH_DELAY_SEC)
            with open("/sys/class/gpio/gpio{}/value".format(pinNum), "w") as pin:
                pin.write(PIN_LOW)
            time.sleep(LED_FLASH_DELAY_SEC)
    except OSError:
        logging.warn("Error writing to pin {}".format(pinNum))
        return False
    return True


def readPin(pinNum):
    """Read the value from some input pin"""
    logging.info("Reading pin {}".format(pinNum))
    try:
        with open("/sys/class/gpio/gpio{}/value".format(pinNum), 'r') as pin:
            return str(pin.read(1)) == "1"
    except OSError:
        logging.warn("Error reading from pin {}".format(pinNum))
    return -1

def entryPoint():
#if __name__ == "__main__":
    #logging.basicConfig(filename='/root/output.log', filemode='w', level=logging.DEBUG)
    logging.info("Intializing Pins")
    setup_gpio_pin(PIN_LED, "out", 0)
    setup_gpio_pin(PIN_VOLT_3_0, "in", 1) # set the pulldown resistor
    setup_gpio_pin(PIN_VOLT_3_2, "in", 0)
    setup_gpio_pin(PIN_VOLT_3_4, "in", 0)
    setup_gpio_pin(PIN_VOLT_3_6, "in", 0)

    iIteration = 0
    threads = []
    bContinue = True
    logging.info("Starting Monitoring")
    while bContinue:
        # check if voltage is above 3.6V
        PIN_VOLT_ = readPin(PIN_VOLT_3_6)
        logging.info("Value PIN_VOLT_3_6: {}".format(PIN_VOLT_))
        if PIN_VOLT_:
            try:
                with open("/sys/class/gpio/gpio{}/value".format(PIN_LED), "w") as pin:
                    pin.write(PIN_LOW)
            except OSError:
                logging.warn("Error writing to pin {}".format(PIN_LED))
            time.sleep(9)
        else:
            # check if voltage is above 3.4V
            PIN_VOLT_ = readPin(PIN_VOLT_3_4)
            if PIN_VOLT_:
                t = threading.Thread(target=blink_LEDxTimes,
                                     args=(PIN_LED, 1,))
                threads.append(t)
                t.start()
                time.sleep(6)
            else:
                # check if voltage is above 3.2V
                PIN_VOLT_ = readPin(PIN_VOLT_3_2)
                if PIN_VOLT_:
                    t = threading.Thread(target=blink_LEDxTimes,
                                         args=(PIN_LED, 2,))
                    threads.append(t)
                    t.start()
                    time.sleep(4)
                else:
                    # check if voltage is above 3.0V
                    PIN_VOLT_ = readPin(PIN_VOLT_3_0)
                    if PIN_VOLT_:
                        t = threading.Thread(target=blink_LEDxTimes,
                                             args=(PIN_LED, 3,))
                        threads.append(t)
                        t.start()
                        # pin volage above 3V so reset iteration
                        iIteration = 0
                        time.sleep(4)
                    else:
                        # pin voltage is below 3V so we need to do a few
                        # iterations to make sure that we are still getting
                        # the same info each time
                        iIteration += 1
                        if iIteration > 3:
                            bContinue = False
                        else:
                            t = threading.Thread(target=blink_LEDxTimes,
                                                 args=(PIN_LED, 4,))
                            threads.append(t)
                            t.start()

        time.sleep(1)
    logging.info("Exiting for Shutdown\n")
    os.system("shutdown now")
