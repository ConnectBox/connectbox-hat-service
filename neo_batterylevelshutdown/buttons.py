#! /usr/bin/python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import shutil
import os
from . import page_display_image
import time
import neo_batterylevelshutdown.usb as usb
import neo_batterylevelshutdown.hats as hat
import logging

import neo_batterylevelshutdown.globals as globals

# globals was initiated by cli, so no need to re initialize here
# We do the imports here... but function calls inside of the code
if globals.device_type == "RM3":
    import radxa.CM3    # not required
    import OPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "NEO":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "OZ2":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
    import orangepi.zero2
else:
    import RPi.GPIO as GPIO  # pylint: disable=import-error



DEBUG = True

class BUTTONS:
    # This class is for dealing with button presses on the connectbox

    BUTTON_PRESS_BUSY = False  # Prevent dual usage of the handleButtonPress function
    BUTTON_PRESS_TIMEOUT_SEC = 0.25  # Prevent bouncing of the handleButtonPress function
    BUTTON_PRESS_CLEARED_TIME = time.time()  # When was the handleButtonPress was last cleared
    CHECK_PRESS_THRESHOLD_SEC = 3  # Threshold for what qualifies as a long press
    DISPLAY_TIMEOUT_SECS = 120     #screen on time before auto off

    def __init__(self, hat_class, display_class):

        self.display = display_class
        self.hat = hat_class
        self.display_type = display_class.display_type
        self.USABLE_BUTTONS = self.hat.USABLE_BUTTONS
        self.command_to_reference = ''
        self.l = []
        NoMountOrig = 0

    def checkReturn(self, val):
        fp = open('/usr/local/connectbox/brand.txt', "r")
        m = str(fp.read())
        if (('usb0NoMount": 1' in m)  and (x != 1)):
            x = m.find("usb0NoMount")
            if x >= 0:
                x = x + 14
                if m[x] != '1' : m = m[0:(x-2)]+" "+m[(x-1):]
                m = m[0:(x-1)]+str(val)+m[(x+1):]
                try:
                    fp.close()
                    fp = open("/usr/local/connectbox/brand.txt", "w")
                    fp.write(m)
                    logging.info("Wrote File brand.txt file as : "+str(m))
                    fp.close()
                    os.sync()
                except:
                   logging.info("couldn't write the brand.txt file out"+str(m))
            else:
                fp.close()
                logging.info("Error trying to change usb0NoMount value to 1 for copy")
                return(False)
        else:
            fp.close()
            x = 0                               #Hang on to the original value to restore as needed
            time.sleep(2)  # give time for Pause of the Mount
            return(True)

    # pylint: disable=too-many-branches, too-many-branches, too-many-return-statements, too-many-statements
    def executeCommands(self, command):
        '''
         :This is where we will actually be executing the commands
         :param command: the command we want to execute
         :return: Nothing
        '''

        ext = "/content/"

        if not (self.hat.batteryLevelAboveVoltage(self.hat.BATTERY_WARNING_VOLTAGE)):
            return  # If low battery, we can't do admin functions as we may run out of power.

        logging.info("Execute Command: %s", command)

        if command == 'remove_usb':
            logging.debug("In remove usb page")
            while (usb.isUsbPresent() != False):     #check  to see if usb is inserted
                logging.debug("USB still present")
                self.display.showRemoveUsbPage()  # tell them to remove it if so
                self.display.pageStack = 'remove_usb'  # let handleButtonPress know to repeat
                time.sleep(2)
            logging.debug("USB removed")
            self.display.pageStack = 'success'  # let out handleButtonPress know
            self.display.showSuccessPage()  # display our success page

        elif command == 'copy_from_usb':
            logging.info("copy from USB")

            fp = open('/usr/local/connectbox/brand.txt', "r")
            m = str(fp.read())
            logging.info("read /usr/local/connectbox/brand.txt: " + m)
            if 'usb0NoMount": 0' in m:
                NoMountOrig = 0  # Hang on to the original value to restore as needed
                logging.info('Found usb0NoMount": 0')
                x = m.find("usb0NoMount")
                if x >= 0:
                    logging.info("Found the usb0NoMount at location: " + str(x))
                    x = x + 14
                    m = m[0:x - 1] + "1" + m[x + 1:]
                    try:
                        fp.close()
                        fp = open("/usr/local/connectbox/brand.txt", "w")
                        fp.write(m)
                        logging.info("Wrote File brand.txt file as: " + m)
                        fp.close()
                        os.sync()
                    except:
                        logging.info("couldn't write the info back")
                        fp.close()
                else:
                    fp.close()
                    logging.info("Error trying to change usb0NoMount value to 1 for copy")
                    return False
            else:
                fp.close()
                NoMountOrig = 1
                logging.info("NoMountOrig is 1 due to the value being 1 in brand")  # Hang on to the original value to restore as needed
            time.sleep(2)  # give time for Pause of the Mount

            x = "a"
            if (usb.isUsbPresent ('/dev/sd' + x + "1") == False):  # check to see if usb is inserted
                self.display.pageStack = 'insertUSB'
                self.display.showInsertUsbPage()
                while (usb.isUsbPresent() == False):
                    time.sleep(2)
            dev = usb.isUsbPresent('/dev/sda1')
            self.pageStack = 'checkSpace'  # Don't allow the display to turn off
            self.display.showWaitPage("Checking Space")
            logging.info("Using location " +str(dev) + " as media copy location")
            mnt = usb.getMount(dev)
            logging.info("mounting location is: " + mnt)
            if mnt == '/media/usb0':
                logging.info("Moving /media/usb0 to /media/usb11 to be able to copy")
                if not os.path.exists('/media/usb11'):  # check that usb11 exists to be able to move the mount
                    os.mkdir('/media/usb11')  # make the directory
                if not usb.moveMount(mnt, '/media/usb11') == 0:  # see if our remount was successful
                    self.display.pageStack = 'errorMvMnt'
                    self.display.showErrorPage("Moving Mount")  # if not generate error page and exit
                    logging.info("move of " + mnt + " to usb11 failed")
                    self.checkReturn( NoMountOrig)
                    return False
                else:
                    mounts = str(subprocess.check_output(['df']))
                    if not ("/media/usb11" in mounts):
                        logging.info("post mount shows that the mount didn't finish correctly")
                        return False
                    logging.info("move mount completed correctly and we're good to go")
                    mnt = "/media/usb11"
            else:
                logging.info("We are not mounted on /media/usb0")
                logging.info("Starting to find the mount point for: " + dev)
                mnt = usb.getMount(dev)
                logging.info("mount is not USB0 but is: " + mnt)
                if mnt == "":
                    x = 11
                    logging.info("we were not mounted as /media/usb0 and we were supposed to be mounted but are not")
                    while os.path.exists("/media/usb" + str(x)) and x > 1:
                        x -= 1
                    mnt = "/media/usb" + str(x)
                    if not os.path.exists(mnt):
                        os.mkdir(mnt)
                    if usb.mount(dev, mnt):
                        logging.info("mounted USB device as " + mnt + " since it wasn't mounted")

            logging.info("Preparing to check space of source " + mnt)
            if os.path.exists("/media/usb0" + ext):
                logging.info("Destination path already exists, erasing before copy")
                try:
                    x = shutil.rmtree("/media/usb0" + ext)
                except:
                    pass
            (d, s) = usb.checkSpace(mnt,'/media/usb0')  # verify that source is smaller than destination
            logging.info("Space of Destination is: " + str(d) + ", Source: " + str(s) + " at: " + mnt)
            if d < s or s == 0:  # if destination free is less than source we don't have enough space
                if d < s:
                    logging.info("source exceeds destination at" + dev + ext)
                else:
                    logging.info("source is 0 bytes in length so nothing to copy")
                if usb.isUsbPresent(dev) != False:
                    self.display.showRemoveUsbPage()  # show the remove usb page
                    self.display.pageStack = 'remove_usb'  # show we removed the usb key
                    self.command_to_reference = 'remove_usb'
                    while usb.isUsbPresent(dev) != False:
                        time.sleep(3)  # Wait for the key to be removed
                    self.display.pageStack = "success"
                    self.display.showSuccessPage()
                    logging.info("success on removing USB key!")
                    self.checkReturn( NoMountOrig)
                    return(1)
            else:
                logging.info("Space of Destination is ok for source to copy to " + dev + ext)
                # we think we have keys to work with if we go forward from here. where the size is ok for the copy
                logging.info("There is enough space so we will go forward with the copy")
                logging.info("starting to do the copy with device " + mnt + ext)
                self.display.showWaitPage("Copying Files\nSize:" + str(int(s / 1000)) + "MB")
                if usb.copyFiles(mnt, "/media/usb0", ext) > 0:  # see if we copied successfully
                    logging.info("failed the copy. display an error page")
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    self.display.showErrorPage("Failed Copy")  # if not generate error page and exit
                    self.display.pageStack = 'error'
                    self.checkReturn( NoMountOrig)
                    return 1
                else:
                    pass  # we have finished the copy so we want to unmount the media/usb11 and run on the internal
                logging.info("Ok were going to clean up now")
                os.sync()
                usb.unmount(mnt)  # unmount the key
                time.sleep(2)

                z = ord('a')
                curDev = '/dev/sda1'
                while z < ord("k"):
                    if usb.isUsbPresent(curDev) != False:
                        if usb.getMount(curDev) != "":
                            try:
                                usb.umount(usb.getMount(curDev))
                                usb.umount(curDev)
                            except:
                                pass
                        self.display.showRemoveUsbPage()  # show the remove usb page
                        self.display.pageStack = 'remove_usb'  # show we removed the usb key
                        self.command_to_reference = 'remove_usb'
                        hat.displayPowerOffTime = sys.maxsize
                        while usb.isUsbPresent(curDev) != False:
                            time.sleep(3)
                    z += 1  # lets look at the next one
                    curDev = '/dev/sd' + chr(z) + '1'  # create the next curdev
            # We finished the umounts
            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

            logging.debug("succes page now restoring the Usb0NoMount flag")
            self.checkReturn( NoMountOrig)
            return 0


        elif command == 'erase_folder':
            file_exists = False  # in regards to README.txt file
            if (usb.isUsbPresent() != False):
                hat.displayPowerOffTime = sys.maxsize
                self.display.showRemoveUsbPage()                    #show the remove usb page
                self.display.pageStack = 'remove_usb'                #show we removed the usb key
                self.command_to_reference = 'remove_usb'
                while (usb.isUsbPresent() != False):
                    time.sleep(3)                                       #Wait for the key to be removed 
                self.display.pageStack= "success"
                self.display.showSuccessPage()
                logging.info("succes on removing USB key before erase!")
                hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                return

            for file_object in os.listdir('/media/usb0'+ext):
                file_object_path = os.path.join('/media/usb0'+ext, file_object)
                if os.path.isfile(file_object_path):
                    os.unlink(file_object_path)
                else:
                    shutil.rmtree(file_object_path)
            logging.debug("FILES NUKED!!!")

            self.display.pageStack = 'success'
            self.display.showSuccessPage()


        elif command == 'copy_to_usb':
            logging.debug("got to copy to usb code")
            z = ord("a")
            dev = '/dev/sd'+chr(z)+'1'
            hat.displayPowerOffTime = sys.maxsize
            while (usb.isUsbPresent(dev) == False):                         # only checks for one USB key
                self.display.pageStack = 'insertUSB'
                self.display.showInsertUsbPage()
                time.sleep(2)
            dev = usb.isUsbPresent("/dev/sda1")                                  # tell them to inert new keys

            hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
            logging.info("Found USB key at "+dev)
            fp = open('/usr/local/connectbox/brand.txt', "r")
            m = str(fp.read())
            if 'usb0NoMount": 0' in m:
                NoMountOrig = 0                                             #Hang on to the original value to restore as needed
                x = str(m).find("usb0NoMount")
                if x >= 0:
                    x = x+ 14
                    m = m[0:x-1]+"1"+m[x+1:]
                    fp.close()
                    fp = open('/usr/local/connectbox/brand.txt', "w")
                    fp.write(m)
                    logging.info("updated brand.txt ",m)
                    fp.close()
                    os.sync()
                    logging.info("NoMountOrig ="+str(NoMountOrig))
                else:
                    fp.close()
                    logging.info("Error trying to change usb0NoMount value to 1 for copy")
                    return(False)
            else:
                fp.close()
                NoMountOirg = 1                                              #Hang on to the original value to restore as needed
            hat.displayPowerOffTime = sys.maxsize
            self.display.pageStack = 'wait'
            self.display.showWaitPage("Checking Sizes")

            logging.debug("we have found at least one usb to copy to: "+dev)

            mnt = usb.getMount(dev)
            if (mnt == '/media/usb0'):                                               # if the key is mounted on '/media/usb0' then we have to move it.
                logging.info("Moving /media/usb0 to /media/usb11 be able to copy")
                if not os.path.exists('/media/usb11'):                              # check that usb11 exists to be able to move the mount
                    os.mkdir('/media/usb11')                                        # make the directory
                if not usb.moveMount(mnt, '/media/usb11'):                          # see if our remount was successful
                        self.display.showErrorPage("Moving Mount")                  # if not generate error page and exit
                        self.display.pageStack = 'error'
                        os.rmdir("/media/usb11")
                        self.checkReturn( NoMountOrig)
                        hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                        return(1)
                else:
                    if mnt == "":
                        self.display.showErrorPage("USB not mounted")               # if not generate error page and exit
                        self.display.pageStack = 'error'
                        self.checkReturn( NoMountOrig)
                        hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                        return(1)
            else:
                if mnt == "":
                    if not os.path.exists("/media/usb11"):
                        os.mkdir("/media/usb11")
                    try:
                        usb.mount(dev,'/media/usb11')
                        mnt = "/media/usb11"
                    except:
                        self.display.showErrorPage("USB not mounted")
                        self.display.pageStack = 'error'
                        hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                        return(1)

            logging.info("We are getting the size for source: /media/usb0 and destination: "+mnt)
            if os.path.isdir(mnt):
                try:
                    shutil.rmtree((mnt+ext), ignore_errors=True)                        #remove old data from /source/ directory
                except OSError:
                    logging.info("had a problem deleting the destination file: ",+ext)
                    self.display.showErrorPage("failed deletion")
                    self.display.pageStack = 'error'
                    self.checkReturn( NoMountOrig)
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    return(1)
            (d, s) = usb.checkSpace('/media/usb0', mnt)  # verify that source is smaller than destination
            logging.info("Space of Destination is: " + str(d) + ", Source: " + str(s) + " at: " + mnt)
            if d < s or s == 0:  # if destination free is less than source we don't have enough space
                if d < s:
                    logging.info("source exceeds destination at" + dev + ext)
                else:
                    logging.info("source is 0 bytes in length so nothing to copy")
                if usb.isUsbPresent(dev) != False:
                    hat.displayPowerOffTime = sys.maxsize
                    self.display.showRemoveUsbPage()  # show the remove usb page
                    self.display.pageStack = 'remove_usb'  # show we removed the usb key
                    self.command_to_reference = 'remove_usb'
                    while usb.isUsbPresent(dev) != False:
                        time.sleep(3)  # Wait for the key to be removed
                    self.display.pageStack = "success"
                    self.display.showSuccessPage()
                    logging.info("success on removing USB key!")
                    self.checkReturn( NoMountOrig)
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    return(1)
            else:
                logging.info("Space of Destination is ok for source to copy to " + dev + ext)
                # we think we have keys to work with if we go forward from here. where the size is ok for the copy
                logging.info("There is enough space so we will go forward with the copy")
                logging.info("starting to do the copy with device " + mnt + ext)
                self.display.showWaitPage("Copying Files\nSize:" + str(int(s / 1000)) + "MB")
                if usb.copyFiles("/media/usb0", mnt, ext) > 0:  # see if we copied successfully
                    logging.info("failed the copy. display an error page")
                    hat.displayPowerOffTime = sys.maxsize
                    self.display.showErrorPage("Failed Copy")  # if not generate error page and exit
                    self.display.pageStack = 'error'
                    time.sleep(self.DISPLAY_TIMEOUT_SECS)
                    self.display.showRemoveUsbPage()
                    self.display.pageStack = 'remove_usb'
                    while usb.getMount(dev) != False:
                        time.sleep(2)
                    logging.info("we don't know the state of the mount so we just leave it")
                    self.checkReturn( NoMountOrig)
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    return(1)
                else:
                    pass  # we have finished the copy so we want to unmount the media/usb11 and run on the internal
                logging.info("Ok were going to clean up now")
                os.sync()
                usb.unmount(mnt)  # unmount the key
                time.sleep(2)

                z = ord('a')
                curDev = '/dev/sda1'
                while z < ord("k"):
                    if usb.isUsbPresent(curDev) != False:
                        if usb.getMount(curDev) != "":
                            try:
                                usb.umount(usb.getMount(curDev))
                                usb.umount(curDev)
                            except:
                                pass
                        hat.displayPowerOffTime = sys.maxsize
                        self.display.showRemoveUsbPage()  # show the remove usb page
                        self.display.pageStack = 'remove_usb'  # show we removed the usb key
                        self.command_to_reference = 'remove_usb'
                        while usb.isUsbPresent(curDev) != False:
                            time.sleep(3)
                    z += 1  # lets look at the next one
                    curDev = '/dev/sd' + chr(z) + '1'  # create the next curdev
            # We finished the umounts

            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            logging.debug("successss page now restoring the Usb0NoMount flag")
            self.checkReturn( NoMountOrig)
            hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
            return 0

    def handleButtonPress(self, channel):
        '''
        The method was created to handle the button press event.  It will get the time buttons
        pressed and then, based upon other criteria, decide how to control further events.

        :param channel: The pin number that has been pressed and thus is registering a 0
        :return: nothing

        '''

        # For OPi.GPIO, it turns out that the state of the button can be read without
        #  killing the event detect!

        print("we have a button press on channel "+ str(channel))

        logging.info("we had a button press")
        if self.display_type == 'DummyDisplay':                                           # this device has no buttons or display, skip
            return

        # this section is to prevent both buttons calling this method and getting two replies
        if self.BUTTON_PRESS_BUSY:  # if flag is set that means this method is currently being used
            logging.info("skipping button press - BUSY flag")
            return  # skip

        # check the amount of time that has passed since this function has been cleared and
        #  see if it exceeds the timeout set.  This avoids buttons bouncing triggering
        #  this function
        if time.time() - self.BUTTON_PRESS_CLEARED_TIME > self.BUTTON_PRESS_TIMEOUT_SEC:
            self.BUTTON_PRESS_BUSY = True                                                 # if enough time, proceed and set the BUSY flag

        else:  # if not enough time, pass
            logging.debug("return from time.time - self.button_press_cleared_time")
            return

        logging.debug("Handling button press")
        # get time single button was pressed along with the amount of time both buttons were pressed

        print("just before check press time")


        channelTime, dualTime = self.checkPressTime(channel)

        logging.debug("time stamp for channel Time line 137: %s", channelTime)
        logging.debug("time stamp for dualTime line 138: %s", dualTime)

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
            logging.info("hit self.check_press_threshold_sec line 158")
            if channel == self.USABLE_BUTTONS[0]:                                           # this is the left button
                logging.info("Left button: pageStack ="+str(pageStack))
                if pageStack in ['success']:                # return to 1st page of admin stack
                    self.moveToStartPage(channel)
                elif pageStack in ['confirm', 'error']:     # return to first page admin stack
                    self.chooseCancel()
                elif pageStack in ['remove_usb']:            # never reach here... loops elsewhere until they remove the USB stick
                    self.chooseEnter(pageStack)
                else:                                       # anything else, we treat as a moveForward (default) function
                    self.moveForward(channel)
            else:                                                                           # right button
                logging.info("Right button: pageStack ="+str(pageStack))
                if pageStack in ['success']:                # return to 1st page of admin stack
                    self.moveToStartPage(channel)
                elif pageStack == 'status':                 # standard behavior - status stack
                    self.moveBackward(channel)
                elif pageStack in ['error']:                # both conditions return to admin stack
                    self.chooseCancel()
                else:                                       # this is an enter key in the admin stack
                    self.chooseEnter(pageStack)

        # if we have a long press (both are equal or greater than threshold) call switch pages
        elif channelTime >= self.CHECK_PRESS_THRESHOLD_SEC: # dual long push
            logging.info("hit dual button press time, move forward")
            self.switchPages()

    def checkPressTime(self, channel):
        print("top of checkPressTime")

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

       '''

        # otherChannel is the button that has not been passed in by the channel parameter.
        otherChannel = self.USABLE_BUTTONS[0] if channel == self.USABLE_BUTTONS[1] else \
            self.USABLE_BUTTONS[1]

        print("channel = "+str(channel) +"    and otherChannel = " +str(otherChannel))

        # NEO ONLY
        # Temporarily turn off the push button interrupt handler
        #   and turn on the push button pins as regular inputs
        # Note that this is a specific case of buttons being on PG6 and PG7... 
        #  If another implementation is made for NEO, this will need updating.
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x00777777 >/dev/null"
            os.popen(cmd).read()
#            print("done with removing NEO event detects")

        # there are two timers here.  One is for total time the original button was pushed.
        # The second is for when the second button was pushed.  The timer gets restarted if
        # the button is not pressed or is released.  The reason for the recorder is that if
        # it is not kept, then when you let off the second button it will bounce and give a
        # false reading.  Here we keep the highest consecutive time it was pushed.
        startTime = time.time()                                                                 # time original button is pushed
        dualStartTime = time.time()                                                             # time both buttons were pushed.
        dualTimeRecorded = 0                                                                    # to prevent time being reset when letting off of buttons

        while GPIO.input(channel) == 0:                                                         # While original button is being pressed
            if GPIO.input(otherChannel) == 0:                                                   # capture hold time if 2nd button down
                dualButtonTime = time.time() - dualStartTime                                    # How long were both buttons down?
                if dualButtonTime > dualTimeRecorded:
                    dualTimeRecorded = dualButtonTime
            if GPIO.input(otherChannel) == 1:                                                   # move start time up if not pressing other button     
                dualStartTime = time.time()                                                     # reset start time to now
            if (time.time() - startTime) > 4:                                                   # don't stick in this interrupt service forever
                break                                                                           # (note: CHECK_PRESS_THRESHOLD_SEC == 3)

        buttonTime = time.time() - startTime                                                    # How long was the original button down?

#        print(" finished timing buttons")
        print("    buttonTime = "+str(buttonTime)+ "dualTimeRecorded = "+str(dualTimeRecorded))

        # We are through with reading of the button states so turn interrupt handling back on
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x66777777 >/dev/null"
            os.popen(cmd).read()
            print("after NEO re-establish interrupts")

        return buttonTime, dualTimeRecorded


    def chooseCancel(self):
        """ method for use when cancelling a choice"""
        logging.debug("Choice cancelled")
        self.command_to_reference = ''                                                          # really don't want to leave this one loaded
        self.display.switchPages()                                                              # drops back to the admin pages
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def chooseEnter(self, pageStack):
        """ method for use when enter selected"""
        logging.debug("Enter pressed.")
        if pageStack == 'admin':
            if self.display.checkIfLastPage():                                                  # if true, go back to admin pageStack
                self.display.switchPages()                                                      # swap to status pages
            else:
                                                                                                # find page name before we change it
                self.command_to_reference = self.display.getAdminPageName()
                logging.debug("Leaving admin page: %s",
                              self.command_to_reference)
                logging.debug("Confirmed Page shown")
                self.display.showConfirmPage()                  # pageStack now = 'confirm'
        else:
            logging.debug("Choice confirmed")
            self.display.showWaitPage("")
            self.display.pageStack = 'wait'
            logging.debug("Waiting Page shown")
            self.executeCommands(self.command_to_reference)

        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def switchPages(self):
        """method for use on button press to change display options"""
        logging.debug("You have now entered, the SwitchPages")
        self.display.switchPages()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def moveToStartPage(self,channel):
        self.display.moveToStartPage()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS


    def moveForward(self, channel):
        """method for use on button press to cycle display"""
        logging.debug("Processing press on GPIO %s (move forward)", channel)
        self.display.moveForward()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def moveBackward(self, channel):
        """method for use on button press to cycle display"""
        logging.debug("Processing press on GPIO %s (move backward)", channel)
        self.display.moveBackward()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
