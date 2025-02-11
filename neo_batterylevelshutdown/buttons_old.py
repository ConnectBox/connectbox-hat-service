#! /usr/bin/python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import shutil
import os
import neo_batterylevelshutdown.page_display_image
import time
import neo_batterylevelshutdown.usb
import neo_batterylevelshutdown.hats
import json
from neo_batterylevelshutdown.globals import *
import logging
import logging.handlers
import neo_batterylevelshutdown.displays

# globals was initiated by cli, so no need to re initialize here
# We do the imports here... but function calls inside of the code
if globals.device_type == "RM3":
    import CM3    # not required
    import  OPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "NEO":
    import RPi.GPIO as GPIO # pylint: disable=import-error
elif globals.device_type == "OZ2":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
    from orangepi import zero2
else:
    import RPi.GPIO as GPIO # pylint: disable=import-error


DEBUG = True
class BUTTONS:


    # This class is for dealing with button presses on the connectbox

    BUTTON_PRESS_BUSY = False  # Prevent dual usage of the handleButtonPress function
    BUTTON_PRESS_TIMEOUT_SEC = 0.25  # Prevent bouncing of the handleButtonPress function
    BUTTON_PRESS_CLEARED_TIME = time.time()  # When was the handleButtonPress was last cleared
    CHECK_PRESS_THRESHOLD_SEC = 3  # Threshold for what qualifies as a long press
    DISPLAY_TIMEOUT_SECS = 120     #screen on time before auto off



# Function writefile operates on brand.txt and changes the usb0NoMount value to val.
    def writefile(self,val):
        fp = open('/usr/local/connectbox/brand.j2', "r", encoding = 'utf-8')
        Brand = json.loads(fp.read())
        fp.close()
        self.logger.info("read /usr/local/connectbox/brand.j2 ")
        if ((Brand['usb0NoMount'] == '0') and (val == 0)):
            NoMountOrig = 0  # Hang on to the original value to restore as needed
            self.logger.info('Found usb0NoMount": 0')
            return("0")
        elif ((Brand['usb0NoMount'] == '1') and (val == '1')):
            NoMountOrig = 1
            self.logger.info('Found usb0NoMount": 1')
            return("1")
        NoMountOrig = Brand['usb0NoMount']
        Brand['usb0NoMount'] = val
        try:
           fp = open("/usr/local/connectbox/brand.j2", "w", encoding = 'utf-8')
           fp.write(json.dumps(Brand))
           self.logger.info("Wrote File brand.j2 file as ")
           fp.close()
           os.sync()
           return(NoMountOrig)
        except:
           self.logger.info("couldn't write the info back to /usr/local/connectbox/brand.j2")
           fp.close()
           return("")

    def __init__(self, hat_class, display_class):

        handler = logging.handlers.WatchedFileHandler( os.environ.get("LOGFILE", "/var/log/neo-batteryshutdown.log"))
        formatter = logging.Formatter(logging.BASIC_FORMAT)
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(os.environ.get("LOGLEVEL", "INFO"))
        self.logger.addHandler(handler)
        self.display = display_class
        self.hat = hat_class
        self.USABLE_BUTTONS = self.hat.USABLE_BUTTONS
        self.logger.info('creating an instance of neo-batteryshutdown.log')
        self.logger.info("self.hat is now set")
        self.display_type = display_class.display_type
        self.logger.info("self.display_type is now is now set")
        self.command_to_reference = ''
        self.l = []
        NoMountOrig = 0
        self.writefile(0)
        try:
            os.remove("/usr/local/connectbox/creating_menus.txt")
        except:
            pass



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

        self.logger.info("Execute Command: %s", command)

        if command == 'remove_usb':		############################################# Remove USB #########################################################
            self.logger.debug("In remove usb page")
            while (usb.isUsbPresent() != False):     #check  to see if usb is inserted
                self.logger.debug("USB still present")
                self.display.showRemoveUsbPage()  # tell them to remove it if so
                self.display.pageStack = 'remove_usb'  # let handleButtonPress know to repeat
                time.sleep(2)
            self.logger.debug("USB removed")
            self.display.pageStack = 'success'  # let out handleButtonPress know
            self.display.showSuccessPage()  # display our success page

        elif command == 'copy_from_usb':	############################################## Copy from USB #######################################################
            self.logger.info("copy from USB")

            NoMountOrig = self.writefile(1)
            if NoMountOrig == "":
                self.logger.info("brand.j2 file was corrupted for Nousb0Mount")
                return False
            self.logger.info("moving on to check for usb keys")

            while (usb.isUsbPresent() == False):     #check  to see if usb is inserted
                self.logger.info("Ok we didn't find a key so we will try again After new  menus")
                y = 8
                while (y>0) and (usb.isUsbPresent() == False):
                    self.display.pageStack = 'insert_usb'  # let handleButtonPress know to repeat
                    self.display.showInsertUsbPage()
                    time.sleep(4)
                    self.logger.info("we have asked to insert  y value: " + str(y))
                    y =- 1
                if y == 0:
                    self.logger.info("ok we didn't find any and no keys were inserted, we exit")
                    self.display.pageStack = 'NoUSB'
                    self.showNoUsbPage()
                    self.writefile(NoMountOrig)
                    return False
            x = 'a'
            z = ""
            while (x < 'k') and (z == ""):
                z = (os.path.exists("/dev/sd"+x+"1"))
                if (z != False):
                    self.logger.info("found key at location "+x)
                else:
                    x = chr(ord(x)+1)
                    z = ""
            if x > 'k':
                self.logger.info("ok we didn't find any and no keys were inserted, we exit")
                self.display.pageStack = 'NoUSB'
                self.showNoUsbPage()
                self.writefile(NoMountOrig)
                return False

#  Ok we have a USB key inserted
            dev = usb.isUsbPresent('/dev/sd' + x + '1')
            self.pageStack = 'checkSpace'  # Don't allow the display to turn off
            globals.sequence = 0
            self.display.pageStack = 'wait'
            globals.a = "Checking Space"
            self.display.showWaitPage(globals.a)
            self.logger.info("Using location " +str(dev) + " as media copy location")
            mnt = usb.getMount(dev)
            self.logger.info("mounting location is: " + mnt)
            if mnt == '/media/usb0':
                self.logger.info("Moving /media/usb0 to /media/usb11 to be able to copy")
                if not os.path.exists('/media/usb11'):  # check that usb11 exists to be able to move the mount
                    os.mkdir('/media/usb11')  # make the directory
                if usb.moveMount(mnt, '/media/usb11') != 0:  # see if our remount was successful
                    self.display.pageStack = 'errorMvMnt'
                    self.display.showErrorPage("Moving Mount")  # if not generate error page and exit
                    self.logger.info("move of " + mnt + " to usb11 failed")
                    self.writefile(NoMountOrig)
                    return False
                else:
                    mounts = str(subprocess.check_output(['df']))
                    if not ("/media/usb11" in mounts):
                        self.logger.info("post mount shows that the mount didn't finish correctly")
                        self.writefile(NoMountOrig)
                        return False
                    self.logger.info("move mount completed correctly and we're good to go")
                    mnt = "/media/usb11"
            else:
                self.logger.info("Starting to find the mount point for: " + str(dev))
                y = 0
                if mnt == "":
                    if x == 'a': x == 'b'
                    self.logger.info("we were not mounted so we need to find a mount point")
                    if os.path.exists(("/dev/sd" + str(ord(x)+"1"))):
                        mnt = '/media/usb" + str(ord(x) - ord("a"))'
                        usb.mount(dev, mnt)
                        self.logger.info("mounted USB device as " + mnt + " since it wasn't mounted")
                    else:
                        mounts = str(subprocess.check_output(['df']))
                        if not (mnt in mounts):
                            self.display.pageStack = 'No USB'
                            self.display.error("USB Mount Failed")
                            self.writefile(NoMountOrig)
                            return False

# We now have a USB key mounted where we can copy from it.

            self.logger.info("Preparing to check space of source " + mnt)
            if os.path.exists("/media/usb0" + ext):
                self.logger.info("Destination path already exists, erasing before copy")
                try:
                    x = shutil.rmtree("/media/usb0" + ext)
                except:
                    pass
            elif os.path.exists("/media/usb0"):
                os.mkdir("/media/usb0/content/", mode=755)
            else:
                logging.info("We somehow lost our USB key on the copy function")
                return False
            (d, s) = usb.checkSpace(mnt,'/media/usb0')  # verify that source is smaller than destination
            self.logger.info("Space of Destination is: " + str(d) + ", Source: " + str(s) + " at: " + mnt)
            if d < s or s == 0:  # if destination free is less than source we don't have enough space
                if d < s:
                    self.logger.info("source exceeds destination at" + str(dev) + str(ext))
                else:
                    self.logger.info("source is 0 bytes in length so nothing to copy")
                if usb.isUsbPresent(dev) != False:
                    self.display.showRemoveUsbPage()  # show the remove usb page
                    self.display.pageStack = 'remove_usb'  # show we removed the usb key
                    self.command_to_reference = 'remove_usb'
                    while usb.isUsbPresent(dev) != False:
                        time.sleep(3)  # Wait for the key to be removed
                    self.display.pageStack = "success"
                    self.display.showSuccessPage()
                    self.logger.info("success on removing USB key!")
                    self.writefile(NoMountOrig)
                    return(1)
            else:
                self.logger.info("Space of Destination is ok for source to copy to " + str(dev) + str(ext))
                # we think we have keys to work with if we go forward from here. where the size is ok for the copy
                self.logger.info("There is enough space so we will go forward with the copy")
                self.logger.info("starting to do the copy with device " + mnt + ext)
                globals.sequence = 0
                globals.a = ("Copying Files\nSize:" + str(int(s / 1000000)) + "MB")
                self.display.showWaitPage(globals.a)
#    Point of calling copy function from usb.py
                if usb.copyFiles(mnt, "/media/usb0", ext, globals.a) > 0:  # see if we copied successfully
                    self.logger.info("failed the copy. display an error page")
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    self.display.showErrorPage("Failed Copy")  # if not generate error page and exit
                    self.display.pageStack = 'error'
                    self.writefile(NoMountOrig)
                    os.sync()
                    return 1
                self.logger.info("Ok were going to clean up now")
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
            self.writefile(NoMountOrig)
            self.logger.debug("succes page now restoring the Usb0NoMount flag")
            return 0


        elif command == 'erase_folder':				############################################ Erase Folder ################################################
            file_exists = False  # in regards to Connectbox.txt file
            if (usb.isUsbPresent() != False):			    #Not allowed to erase USB keys.
                logging.info("need to remove the USB before we erase folders")
                hat.displayPowerOffTime = sys.maxsize
                self.display.showRemoveUsbPage()                    #show the remove usb page
                self.display.pageStack = 'remove_usb'                #show we removed the usb key
                self.command_to_reference = 'remove_usb'
                while (usb.isUsbPresent() != False):
                    time.sleep(3)                                       #Wait for the key to be removed 
                logging.info("Ok USB has now been removed" )
                self.display.pageStack= "success"
                self.display.showSuccessPage()				#Success on removing the USB key
                self.logger.info("succes on removing USB key before erase!")
                hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                return
            logging.info("Ok we have no USB key loaded to we will nuke the local files") # ok we will log that we are starting to erase the internal uSD storage of /'content'
            self.logger.info("Erasing internal sorage")
            self.display.pageStack = 'wait'
            self.display.showWaitPage("Erasing Internal" + chr(10) + "Storage")
            for file_object in os.listdir('/media/usb0'+ext):
                file_object_path = os.path.join('/media/usb0'+ext, file_object)
                if os.path.isfile(file_object_path):
                    os.unlink(file_object_path)
                else:
                    shutil.rmtree(file_object_path)
            self.logger.info("FILES NUKED!!!")

            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
            return()

        elif command == 'copy_to_usb':				############################################## Copy to USB ###################################################
            self.logger.debug("got to copy to usb code")
            devs = str(subprocess.check_output(['ls /dev/']))
            z = 'a'
            dev = '/dev/sd'+chr(z)+'1'
            while (dev not in devs) and z <= 'z':	                         # only checks for one USB key
                z +=1
                dev = '/dev/sd'+chr(z)+'1' 
            NoMountOrig = self.writefile("1")
            if z > 'z':
                self.display.pageStack = 'insertUSB'
                self.display.showInsertUsbPage()
                hat.displayPowerOffTime = sys.maxsize
                time.sleep(2)
            zz = True
            while ((z > 'z') and zz):
                devs = str(subprocess.check_output(['ls /dev/']))
                dev = '/dev/sd'+chr(z)+'1'
                if (dev not in devs):
                    z += 1
                    if z >= 'z': z='a'
                else: zz = False
            dev = usb.isUsbPresent(dev)                                          # tell them to inert new keys
            hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
            self.logger.info("Found USB key at "+str(dev))
            hat.displayPowerOffTime = sys.maxsize
            self.display.pageStack = 'wait'
            globals.sequence = 0
            globals.a = "Checking Sizes"
            self.display.showWaitPage(globals.a)
            self.logger.debug("we have found at least one usb to copy to: "+dev)

            mnt = usb.getMount(dev)
            if ((mnt != "") and (mnt == '/media/usb0')):
                self.logger.info("Moving /media/usb0 to /media/usb11 be able to copy")
                if not os.path.exists('/media/usb11'):                              # check that usb11 exists to be able to move the mount
                    os.mkdir('/media/usb11')                                        # make the directory
                elif usb.getMount('/media/usb11') != "":
                    usb.unmount(usb.getDev('/media/usb11'))
                if not usb.moveMount(mnt, '/media/usb11'):                          # see if our remount was successful
                    self.display.showErrorPage("Moving Mount")                      # if not generate error page and exit
                    self.display.pageStack = 'error'
                    os.rmdir("/media/usb11")
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    self.writefile(NoMountOrig)
                    return(1)
                else:
                    if mnt == "":
                        self.display.showErrorPage("USB not mounted")               # if not generate error page and exit
                        self.display.pageStack = 'error'
                        hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                        self.writefile(NoMountOrig)
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
                        self.writefile(NoMountOrig)
                        return(1)

            self.logger.info("We are getting the size for source: /media/usb0 and destination: "+mnt)
            if os.path.isdir(mnt):
                try:
                    shutil.rmtree((mnt+ext), ignore_errors=True)                        #remove old data from /source/ directory
                except OSError:
                    self.logger.info("had a problem deleting the destination file: ",+ext)
                    self.display.showErrorPage("failed deletion")
                    self.display.pageStack = 'error'
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    self.writefile(NoMountOrig)
                    return(1)
            (d, s) = usb.checkSpace('/media/usb0', mnt)  # verify that source is smaller than destination
            self.logger.info("Space of Destination is: " + str(d) + ", Source: " + str(s) + " at: " + mnt)
            if d < s or s == 0:  # if destination free is less than source we don't have enough space
                if d < s:
                    self.logger.info("source exceeds destination at" + dev + ext)
                else:
                    self.logger.info("source is 0 bytes in length so nothing to copy")
                if usb.isUsbPresent(dev) != False:
                    hat.displayPowerOffTime = sys.maxsize
                    self.display.showRemoveUsbPage()  # show the remove usb page
                    self.display.pageStack = 'remove_usb'  # show we removed the usb key
                    self.command_to_reference = 'remove_usb'
                    while usb.isUsbPresent(dev) != False:
                        time.sleep(3)  # Wait for the key to be removed
                    self.display.pageStack = "success"
                    self.display.showSuccessPage()
                    self.logger.info("success on removing USB key!")
                    self.writefile(NoMountOrig)
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    return(1)
            else:
                self.logger.info("Space of Destination is ok for source to copy to " + dev + ext)
                # we think we have keys to work with if we go forward from here. where the size is ok for the copy
                self.logger.info("There is enough space so we will go forward with the copy")
                self.logger.info("starting to do the copy with device " + mnt + ext)
                globals.sequence = 0
                globals.a = ("Copying Files\nSize:" + str(int(s / 1076413)) + "MB")
                self.display.showWaitPage(globals.a)
                if usb.copyFiles("/media/usb0", mnt, ext, globals.a ) > 0:  # see if we copied successfully
                    self.logger.info("failed the copy. display an error page")
                    hat.displayPowerOffTime = sys.maxsize
                    self.display.showErrorPage("Failed Copy")  # if not generate error page and exit
                    self.display.pageStack = 'error'
                    time.sleep(self.DISPLAY_TIMEOUT_SECS)
                    self.display.showRemoveUsbPage()
                    self.display.pageStack = 'remove_usb'
                    while usb.getMount(dev) != False:
                        time.sleep(2)
                    self.logger.info("we don't know the state of the mount so we just leave it")
                    self.writefile(NoMountOrig)
                    hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
                    return(1)
                else:
                    pass  # we have finished the copy so we want to unmount the media/usb11 and run on the internal
                self.logger.info("Ok were going to clean up now")
                os.sync()
                usb.unmount(mnt)  # unmount the key
                usb.unmount(dev)
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
            self.logger.debug("successss page now restoring the Usb0NoMount flag")
            hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
            self.writefile(NoMountOrig)
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

        self.logger.info("we had a button press")
        if self.display_type == 'DummyDisplay':                                           # this device has no buttons or display, skip
            return

        # this section is to prevent both buttons calling this method and getting two replies
        if self.BUTTON_PRESS_BUSY:  # if flag is set that means this method is currently being used
            self.logger.info("skipping button press - BUSY flag")
            return  # skip

        # check the amount of time that has passed since this function has been cleared and
        #  see if it exceeds the timeout set.  This avoids buttons bouncing triggering
        #  this function
        if time.time() - self.BUTTON_PRESS_CLEARED_TIME > self.BUTTON_PRESS_TIMEOUT_SEC:
            self.BUTTON_PRESS_BUSY = True                                                 # if enough time, proceed and set the BUSY flag

        else:  # if not enough time, pass
            self.logger.debug("return from time.time - self.button_press_cleared_time")
            return

        self.logger.debug("Handling button press")
        # get time single button was pressed along with the amount of time both buttons were pressed

        print("just before check press time")


        channelTime, dualTime = self.checkPressTime(channel)

        self.logger.debug("time stamp for channel Time line 137: %s", channelTime)
        self.logger.debug("time stamp for dualTime line 138: %s", dualTime)

        # clear the CHECK_PRESS_BUSY flag
        self.BUTTON_PRESS_BUSY = False

        # reset the CHECK_PRESS_CLEARED_TIME to now
        self.BUTTON_PRESS_CLEARED_TIME = time.time()

        pageStack = self.display.pageStack  # shortcut
        self.logger.debug("PAGESTACK: %s", pageStack)
        self.logger.debug("COMMAND: %s", self.command_to_reference)

        # this is where we decide what to do with the button press.  ChanelTime is the first
        # button pushed, dualTime is the amount of time both buttons were pushed.
        if channelTime < .1:  # Ignore noise
            pass

        # if either button is below the press threshold, treat as normal
        elif channelTime < self.CHECK_PRESS_THRESHOLD_SEC or \
                dualTime < self.CHECK_PRESS_THRESHOLD_SEC:
            self.logger.info("hit self.check_press_threshold_sec line 158")
            if channel == self.USABLE_BUTTONS[0]:                                           # this is the left button
                self.logger.info("Left button: pageStack ="+str(pageStack))
                if pageStack in ['success']:                # return to 1st page of admin stack
                    self.moveToStartPage(channel)
                elif pageStack in ['confirm', 'error']:     # return to first page admin stack
                    self.chooseCancel()
                elif pageStack in ['remove_usb']:            # never reach here... loops elsewhere until they remove the USB stick
                    self.chooseEnter(pageStack)
                else:                                       # anything else, we treat as a moveForward (default) function
                    self.moveForward(channel)
            else:                                                                           # right button
                self.logger.info("Right button: pageStack ="+str(pageStack))
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
            self.logger.info("hit dual button press time, move forward")
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
        self.logger.debug("Choice cancelled")
        self.command_to_reference = ''                                                          # really don't want to leave this one loaded
        self.display.switchPages()                                                              # drops back to the admin pages
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def chooseEnter(self, pageStack):
        """ method for use when enter selected"""
        self.logger.debug("Enter pressed.")
        if pageStack == 'admin':
            if self.display.checkIfLastPage():                                                  # if true, go back to admin pageStack
                self.display.switchPages()                                                      # swap to status pages
            else:
                                                                                                # find page name before we change it
                self.command_to_reference = self.display.getAdminPageName()
                self.logger.debug("Leaving admin page: %s",
                              self.command_to_reference)
                self.logger.debug("Confirmed Page shown")
                self.display.showConfirmPage()                  # pageStack now = 'confirm'
        else:
            self.logger.debug("Choice confirmed")
            globals.sequence = 0
            self.display.showWaitPage()
            self.display.pageStack = 'wait'
            self.logger.debug("Waiting Page shown")
            self.executeCommands(self.command_to_reference)

        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def switchPages(self):
        """method for use on button press to change display options"""
        self.logger.debug("You have now entered, the SwitchPages")
        self.display.switchPages()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def moveToStartPage(self,channel):
        self.display.moveToStartPage()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS


    def moveForward(self, channel):
        """method for use on button press to cycle display"""
        self.logger.debug("Processing press on GPIO %s (move forward)", channel)
        self.display.moveForward()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def moveBackward(self, channel):
        """method for use on button press to cycle display"""
        self.logger.debug("Processing press on GPIO %s (move backward)", channel)
        self.display.moveBackward()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
