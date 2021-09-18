# -*- coding: utf-8 -*-

import subprocess
import shutil
import time
import logging
import os
import RPi.GPIO as GPIO  # pylint: disable=import-error
from .usb import USB
import neo_batterylevelshutdown.globals as globals


class BUTTONS:
    # This class is for dealing with button presses on the connectbox

    BUTTON_PRESS_BUSY = False  # Prevent dual usage of the handleButtonPress function
    BUTTON_PRESS_TIMEOUT_SEC = 0.25  # Prevent bouncing of the handleButtonPress function
    BUTTON_PRESS_CLEARED_TIME = time.time()  # When was the handleButtonPress was last cleared
    CHECK_PRESS_THRESHOLD_SEC = 3  # Threshold for what qualifies as a long press

    def __init__(self, hat_class, display_class):
        self.display = display_class
        self.hat = hat_class
        self.display_type = display_class.display_type
        self.USABLE_BUTTONS = self.hat.USABLE_BUTTONS
        self.command_to_reference = ''

    # pylint: disable=too-many-branches, too-many-branches, too-many-return-statements, too-many-statements
    def executeCommands(self, command):
        '''
        This is where we will actually be executing the commands

        :param command: the command we want to execute
        :return: Nothing
        '''

        logging.debug("Execute Command: %s", command)
        usb = USB()
        if command == 'remove_usb':
            logging.debug("In remove usb page")
            if usb.isUsbPresent():                          # check to see if usb is inserted
                logging.debug("USB still present")
                self.display.showRemoveUsbPage()            # tell them to remove it if so
                self.display.pageStack = 'removeUsb'        # let handleButtonPress know to repeat
                self.command_to_reference = 'remove_usb'    # let executeCommands know what we want
            else:                                           # if they were good and removed USB
                logging.debug("USB removed")
                self.display.pageStack = 'success'          # let out handleButtonPress know
                self.display.showSuccessPage()              # display our success page

        if command == 'copy_from_usb':
            if not usb.isUsbPresent():                  # check to see if usb is inserted
                self.display.showNoUsbPage()            # if not, alert as this is required
                self.display.pageStack = 'error'
                return                                  # cycle back to menu
            if not usb.moveMount():             # see if our remount was successful
                self.display.showErrorPage()    # if not generate error page and exit
                self.display.pageStack = 'error'
                return
            if not usb.checkSpace():            # verify that source is smaller than destination
                self.display.showNoSpacePage()  # if not, alert as this is a problem
                usb.moveMount(curMount='/media/usb1', destMount='/media/usb0')
                self.display.pageStack = 'error'
                return
            if not usb.copyFiles():                 # see if we copied successfully
                self.display.showErrorPage()        # if not generate error page and exit
                self.display.pageStack = 'error'
                return
            if not usb.unmount('/media/usb1'):      # see if we were able to unmount /media/usb1
                self.display.showErrorPage()        # if not generate error page and exit
                self.display.pageStack = 'error'
                return
            # if we're here we successfully unmounted /media/usb1
            if usb.isUsbPresent():  # if usb is present, have the remove it
                self.display.showRemoveUsbPage()           # show the remove usb page
                self.display.pageStack = 'removeUsb'  # so our controller knows what to do
                self.command_to_reference = 'remove_usb'   # will cause another check
                return
            self.display.pageStack = 'success'  # if the usb was removed
            self.display.showSuccessPage()      # display success page

        elif command == 'erase_folder':
            file_exists = False  # in regards to README.txt file
            if usb.isUsbPresent():
                self.display.pageStack = 'error'
                self.display.showRemoveUsbPage()
                return
            if os.path.isfile('/media/usb0/README.txt'):  # keep the default README if possible
                file_exists = True
                subprocess.call(['cp', '/media/usb0/README.txt', '/tmp/README.txt'])
                logging.debug("README.txt moved")
            for file_object in os.listdir('/media/usb0'):
                file_object_path = os.path.join('/media/usb0', file_object)
                if os.path.isfile(file_object_path):
                    os.unlink(file_object_path)
                else:
                    shutil.rmtree(file_object_path)
            logging.debug("FILES NUKED!!!")
            if file_exists:
                subprocess.call(['mv', '/tmp/README.txt', '/media/usb0/README.txt'])  # move back
                logging.debug("README.txt returned")
            logging.debug("Life is good!")
            self.display.pageStack = 'success'
            self.display.showSuccessPage()

    def handleButtonPress(self, channel):
        '''
        The method was created to handle the button press event.  It will get the time buttons
        pressed and then, based upon other criteria, decide how to control further events.

        :param channel: The pin number that has been pressed and thus is registering a 0
        :return: nothing

        '''

        if self.display_type == 'DummyDisplay':  # this device has no buttons or display, skip
            return

        # this section is to prevent both buttons calling this method and getting two replies
        if self.BUTTON_PRESS_BUSY:  # if flag is set that means this method is currently being used
            return  # skip

        # check the amount of time that has passed since this function has been cleared and
        #  see if it exceeds the timeout set.  This avoids buttons bouncing triggering
        #  this function
        if time.time() - self.BUTTON_PRESS_CLEARED_TIME > self.BUTTON_PRESS_TIMEOUT_SEC:
            self.BUTTON_PRESS_BUSY = True  # if enough time, proceed and set the BUSY flag

        else:  # if not enough time, pass
            return

        logging.debug("Handling button press")
        # get time single button was pressed along with the amount of time both buttons were pressed
        channelTime, dualTime = self.checkPressTime(channel)

        # clear the CHECK_PRESS_BUSY flag
        self.BUTTON_PRESS_BUSY = False

        # reset the CHECK_PRESS_CLEARED_TIME to now
        self.BUTTON_PRESS_CLEARED_TIME = time.time()

        pageStack = self.display.pageStack  # shortcut
        logging.debug("PAGESTACK: %s", pageStack)
        logging.debug("COMMAND: %s", self.command_to_reference)

        # this is where we decide what to do with the button press.  ChanelTime is the first
        # button pushed, dualTime is the amount of time both buttons were pushed.
        if channelTime < .1:  # Ignore noise
            pass

        # if either button is below the press threshold, treat as normal
        elif channelTime < self.CHECK_PRESS_THRESHOLD_SEC or \
                dualTime < self.CHECK_PRESS_THRESHOLD_SEC:
            if channel == self.USABLE_BUTTONS[0]:  # this is the left button
                if pageStack in ['confirm', 'error', 'success']: # return to admin stack
                    self.chooseCancel()
                elif pageStack in ['removeUsb']: # gonna keep going until they remove the USB stick
                    self.chooseEnter(pageStack)
                else: # anything else, we treat as a moveForward (default) function
                    self.moveForward(channel)
            else:  # right button
                if pageStack == 'status':  # standard behavior
                    self.moveBackward(channel)
                elif pageStack in ['error', 'success']:  # both conditions return to admin stack
                    self.chooseCancel()
                else:  # this is an enter key
                    self.chooseEnter(pageStack)

        # if we have a long press (both are equal or greater than threshold) call switch pages
        elif channelTime >= self.CHECK_PRESS_THRESHOLD_SEC: # dual long push
            self.switchPages()

    def checkPressTime(self, channel):
        '''
        This method checks for a long double press of the buttons.  Previously, we only
        had to deal with a single press of a single button.

        This method requires two pins which are contained in the USABLE_BUTTONS list constant.
        This was necessary because different HATs use different pins.  This list will be used
        for two things.  One, to determine which is the non-button pressed, this is done by
        comparing the channel passed in to the first item in the list.  If it is not the first
        item, it must be the second.  Two, if there is no double long press, then the
          information is used to decide which method applies to which pin.  The first item in the
          list is the left button, the second item is the second button.

         If there is a double long press, we call a swapPages method.

        :param channel: The pin number that has been pressed and thus is registering a 0
        :return: time original button pressed, time both buttons were pressed

        Note that the RPi.GPIO_NP_CB library invalidates the GPIO.input() function when the
        GPIO.add_event_detect() function is invoked. To work around this we will use the
        GPIO.remove_event_detect() function and add the GPIO.setup() function (for BOTH push button
        pins) at the top of the checkPressTime() routine. This will make the 
        GPIO.input() functional for the pushbuttons. Then we will re-establish the GPIO.add_event_detect()
        for both push buttons before leaving this routine to re-enable interrupt servicing for push button
        action. 
       
        '''

        
        # otherChannel is the button that has not been passed in by the channel parameter.
        otherChannel = self.USABLE_BUTTONS[0] if channel == self.USABLE_BUTTONS[1] else \
            self.USABLE_BUTTONS[1]
        
        # Temporarily turn off the push button interrupt handler
        #   and turn on the push button pins as regular inputs
        # Note that this is a specific case of buttons being on PG6 and PG7... 
        #  If another implementation is made for NEO, this will need updating.
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x00777777"
            retval = os.system(cmd)

         
        # there are two timers here.  One is for total time the original button was pushed.
        # The second is for when the second button was pushed.  The timer gets restarted if
        # the button is not pressed or is released.  The reason for the recorder is that if
        # it is not kept, then when you let off the second button it will bounce and give a
        # false reading.  Here we keep the highest consecutive time it was pushed.
        startTime = time.time()     # time original button is pushed
        dualStartTime = time.time() # time both buttons were pushed.
        dualTimeRecorded = 0        # to prevent time being reset when letting off of buttons

        while GPIO.input(channel) == 0:         # While original button is being pressed
            if GPIO.input(otherChannel) == 1:   # move start time up if not pressing other button
                dualButtonTime = time.time() - dualStartTime # How long were both buttons down?
                if dualButtonTime > dualTimeRecorded:
                    dualTimeRecorded = dualButtonTime
                dualStartTime = time.time()     # reset start time to now
            if (time.time() - startTime) > 5:   # don't stick in this interrupt service forever
                break    

        buttonTime = time.time() - startTime    # How long was the original button down?

        # We are through with reading of the button states so turn interrupt handling back on
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x66777777"
            retval = os.system(cmd)

        return buttonTime, dualTimeRecorded

    def chooseCancel(self):
        """ method for use when cancelling a choice"""
        logging.debug("Choice cancelled")
        self.command_to_reference = ''  # really don't want to leave this one loaded
        self.display.switchPages()      # drops back to the admin pages
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

    def chooseEnter(self, pageStack):
        """ method for use when enter selected"""
        logging.debug("Enter pressed.")
        if pageStack == 'admin':
            if self.display.checkIfLastPage():  # if true, go back to admin pageStack
                self.display.switchPages()      # swap to status pages
            else:
                # find page name before we change it
                self.command_to_reference = self.display.getAdminPageName()
                logging.debug("Leaving admin page: %s",
                              self.command_to_reference)
                logging.debug("Confirmed Page shown")
                self.display.showConfirmPage()
        else:
            logging.debug("Choice confirmed")
            self.display.showWaitPage()
            self.display.pageStack = 'wait'
            logging.debug("Waiting Page shown")
            self.executeCommands(self.command_to_reference)

        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

    def switchPages(self):
        """method for use on button press to change display options"""
        logging.debug("You have now entered, the SwitchPages")
        self.display.switchPages()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

    def moveForward(self, channel):
        """method for use on button press to cycle display"""
        logging.debug("Processing press on GPIO %s (move forward)", channel)
        self.display.moveForward()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

    def moveBackward(self, channel):
        """method for use on button press to cycle display"""
        logging.debug("Processing press on GPIO %s (move backward)", channel)
        self.display.moveBackward()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS
