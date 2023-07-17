# -*- coding: utf-8 -*-

import subprocess
import sys
import shutil
import time
import logging
import os
import RPi.GPIO as GPIO                                                     # pylint: disable=import-error from .usb import USB from . import page_display_image import
from .usb import USB
from . import page_display_image
import neo_batterylevelshutdown.globals as globals
DEBUG = True

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
        self.l = []


    def checkReturn(self, x)
        with open('/usr/local/connectbox/brand.txt', "a") as fp:
            m = fp.read()
            if (('usb0NoMount":1' in m) and (x != 1)):
                x = str(m).find("usb0NoMount")
                if x >= 0:
                    m[x+13:x+13] = str(x)
                    fp.write(m)
                else:   
                    fp.close()
                    os.sync()
                    logging.info("Error trying to change usb0NoMount value to 1 for copy")
                    return(False)
            else: x = 0                               #Hang on to the original value to restore as needed
                fp.close()
                os.sync()
                time.sleep(2)  # give time for Pause of the Mount
                return(True)

    # pylint: disable=too-many-branches, too-many-branches, too-many-return-statements, too-many-statements
    def executeCommands(self, command):
        '''
        This is where we will actually be executing the commands

        :param command: the command we want to execute
        :return: Nothing
        '''

        ext = "/content/"

        logging.debug("Execute Command: %s", command)
        usb = USB()
        if command == 'remove_usb':
            logging.debug("In remove usb page")
            if usb.isUsbPresent():                                              # check to see if usb is inserted
                logging.debug("USB still present")
                self.display.showRemoveUsbPage()                                # tell them to remove it if so
                self.display.pageStack = 'removeUsb'                            # let handleButtonPress know to repeat
                self.command_to_reference = 'remove_usb'                        # let executeCommands know what we want
            else:                                                               # if they were good and removed USB
                logging.debug("USB removed")
                self.display.pageStack = 'success'                              # let out handleButtonPress know
                self.display.showSuccessPage()                                  # display our success page

        if command == 'copy_from_usb':

            logging.info("copy from USB")
            x = ord("a")
            while(not usb.isUsbPresent('/dev/sd'+chr(x)+"1") and x < ord("k")): # check to see if usb is inserted
                x += 1
            if x == ord("k"):
                self.display.showNoUsbPage()                                    # if not, alert as this is required
                self.display.pageStack = 'error'
                return                                                          # cycle back to menu
            dev = '/dev/sd'+chr(x)+'1'
            self.pageStack = 'wait'                                             # Dont allow the display to turn off
            self.display.showWaitPage("Checking Space")
            logging.info("Using location "+dev+" as media copy location")
            if usb.getMount(dev) == '/media/usb0':
                with open('/usr/local/connectbox/brand.txt', "a") as fp:
                    m = fp.read()
                    if 'usb0NoMount":0' in m:
                        NoMountOrig = 0                                #Hang on to the original value to restore as needed
                        x = str(m).find("usb0NoMount")
                        if x >= 0:
                            m[x+13:x+13] = "1"
                            fp.write(m)
                        else:
                            fp.close()
                            os.sync()
                            logging.info("Error trying to change usb0NoMount value to 1 for copy")
                            return(False)
                    else: NoMountOirg = 1                               #Hang on to the original value to restore as needed
                fp.close()
                os.sync()
                time.sleep(2)  # give time for Pause of the Mount
                logging.debug("Moving /media/usb0 to /media/usb11 to be able to copy")
                if not os.path.exists('/media/usb11'):                          # check that usb11 exsists to be able to move the mount
                    os.mkdir('/media/usb11')                                    # make the directory
                if not usb.moveMount(dev, usb.getMount(dev), '/media/usb11'):     # see if our remount was successful
                    self.display.showErrorPage("Moving Mount")                  # if not generate error page and exit
                    self.display.pageStack = 'error'
                    logging.info("move of usb0 to usb11 failed")
                    checkReturn(self, NoMountOrig)
                   return
            logging.info("Preparing to check space of source "+(usb.getMount(dev)))
            self.display.showWaitPage("Checking Space\n    "+str(dev))
            (d,s) = usb.checkSpace(usb.getMount(dev))                           # verify that source is smaller than destination
            logging.info("space checked source : "+str(s)+", destination : "+str(d)+" device "+dev)
            if s > d:
                logging.debug("There is not enough space we will call an error on "+dev)
                self.display.showNoSpacePage(1, dev )                           # if not, alert as this is a problem
                self.display.pageStack ='error'
                if usb.getMount(dev) == '/media/usb11':
                    logging.debug("since we moved the mount we want /media/usb0 back")
                    usb.moveMount(dev, '/media/usb11', '/media/usb0')
                    try: os.rmdir('/media/usb11')
                    except:
                        pass
                    logging.info("move back of usb11 to usb0 was done")
                checkReturn(self, NoMountOrig)
                return
            a = usb.getMount(dev)
            logging.info("starting to do the copy with device "+a+ext)
            self.display.showWaitPage("Copying Files\nSize:"+str(int(s/1000))+"MB")
            if not usb.copyFiles(a, "/media/usb0", ext):                    # see if we copied successfully
                logging.info("failed the copy. display an error page")
                self.display.showErrorPage("Failed Copy")                   # if not generate error page and exit
                self.display.pageStack = 'error'
                if usb.getMount(dev) == '/media/usb11' :
                    logging.info("since we moved the mount we want /media/usb0 back")
                    usb.moveMount(dev, "/media/usb11", "/media/usb0")
                    # we have finished the copy so we want to unmount the media/usb11 and run on the internal
            else:
                os.sync()
                umount("/media/usb11")
                time.sleep(2)
                try: os.rmdir('/media/usb11')
                except:
                    pass
                while usb.isUsbPresent(dev):
                    self.display.showRemoveUsbPage()                    #show the remove usb page
                    self.display.pageStack = 'removeUsb'                #show we removed the usb key
                    self.command_to_reference = 'remove_usb'
                    while usb.isUsbPresent(dev):
                        time.sleep(3)                                       #Wait for the key to be removed 
                self.display.pageStack= "success"
                self.display.showSuccessPage()
                logging.info("succes on removing USB key after copy")
                checkReturn(self, NoMountOrig)   
                return


        elif command == 'erase_folder':
            file_exists = False  # in regards to README.txt file
            if usb.isUsbPresent():
                self.display.pageStack = 'error'
                self.display.showRemoveUsbPage()
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
            z = ord('a')                                                    # Z is the ordinal of the USB key in DEV
            dev = '/dev/sd'+chr(z)+'1' 
            if (not usb.isUsbPresent(dev)):                                 # only checks /dev/sda1...
                self.display.showInsertUsbPage()                            # tell them to inert new keys
   
            if usb.isUsbPresent('/dev/sdk1'):                               #check for more USB's than we can handle
                self.display.showRemoveUsbPage("To many USB's\nMaximum 10")
                self.command_to_reference = 'remove_usb'
                self.display.pageStack = 'removeUsb'                                #show we removed the usb key
                time.sleep(3)                                                       #wait 3 seconds and check again.

            while (not usb.isUsbPresent(dev)) and z < ord('k'):         # loop to find /dev/sdxx
                z += 1
                dev = '/dev/sd'+chr(z)+'1'
                if z == ord('k'):
                    z = ord('a')
                    dev = '/dev/sd'+chr(z)+'1'

            with open('/usr/local/connectbox/brand.txt', "a") as fp:
                m = fp.read()
                if 'usb0NoMount":0' in m:
                    NoMountOrig = 0                                #Hang on to the original value to restore as needed
                    x = str(m).find("usb0NoMount")
                    if x >= 0:
                        m[x+13:x+13] = "1"
                        fp.write(m)
                    else:
                        fp.close()
                        os.sync()
                        logging.info("Error trying to change usb0NoMount value to 1 for copy")
                        return(False)
                else: NoMountOirg = 1                               #Hang on to the original value to restore as needed
            fp.close()
            os.sync()
            self.display.pageStack = 'wait'
            self.display.showWaitPage("Checking Sizes")

            logging.debug("we have found at least one usb to copy to: "+dev)

            y = 0                                                                   # y keeps track of the number of USB keys
            logging.debug("were ready to start size check")
            while z < ord('k'):
                if usb.getMount(dev) == '/media/usb0':                              # if the key is mounted on '/media/usb0' then we have to move it.
                    x = ord(":")                                                    # x keeps track of the mount point
                    logging.info("Moving /media/usb0 to /media/usb11 be able to copy")
                    if not os.path.exists('/media/usb11'):                          # check that usb11 exsists to be able to move the mount
                        os.mkdir('/media/usb11')                                    # make the directory
                    if not usb.moveMount( dev, '/media/usb0', '/media/usb11'):      # see if our remount was successful
                        self.display.showErrorPage("Moving Mount")                  # if not generate error page and exit
                        self.display.pageStack = 'error mounting'
                        os.rmdir("/media/usb11")
                        try: os.remove('/usr/local/connectbox/PauseMount')
                        except:
                            pass
                        checkReturn(self, NoMountOrig)
                        return
                else:
                    x = (ord(dev[len(dev)-2])-ord("a"))+ord("0")

                while z < ord('k') and y >= 0:                                       #While we know we have a usb key lets check the sizes
                    zz = usb.getMount(dev)

                    if zz == "":                                            # we have a /dev/sda but it isn't mounted
                        self.display.showErrorPage("USB not mounted")                  # if not generate error page and exit
                        self.display.pageStack = 'error'
                        try: os.remove('/usr/local/connectbox/PauseMount')
                        except:
                            pass
                        checkReturn(self, NoMountOrig)
                        return

                    else:
                        logging.info("getting the size for source /media/usb0 and destination "+zz)
                        if os.path.isdir(zz+ext):
                            try:
                                shutil.rmtree((zz+ext), ignore_errors=True)         #remove old data from /source/ directory
                            except OSError:
                                logging.info("had a problem deleting the destination file: ",zz+ext)
                                checkReturn(self, NoMountOrig)
                                return
                        (d,s) = usb.checkSpace('/media/usb0', zz)             # verify that source is smaller than destination
                        logging.info("Space of Destination  is : "+str(d)+" , Source: "+str(s)+" at: "+dev)
                        if d<s or s==0:                                             #if destination free is less than source we don't have enough space
                            if d<s: logging.info("source exceeds destination at"+zz+ext)
                            else: logging.info("source is 0 bytes in length so nothing to copy")
                            y -= 1
                            while usb.isUsbPresent(dev):
                                logging.info("we found we don't have enough sapce on usb key "+dev)
                                if d<s:
                                    self.display.showNoSpacePage(2, dev )           #alert that there is a problem
                                    os.sync
                                else: self.display.showNoSpacePage(2,"No Source Files")
                                usb.unmount(zz)                                         #Make sure we unmount that device.  
                                usb.unmount(dev)                                        #Make sure we unmount the mount point
                                self.display.pageStack = 'remove_usb'               #remove this usb
                                self.command_to_reference = 'remove_usb'            #let execute commands know what we want
                                time.sleep(4)                                       #wait a second
                            if zz[len(zz)-1] != '0':                                # as long as its not /media/usb0
                                os.system('rm -r '+ zz)                             #Make sure we remove that directory since PauseMount is set
                            self.display.pageStack = 'wait'
                            self.display.showWaitPage("Checking Sizes")             #Ok we have the key removed lets move on.
                            x = (ord(dev[len(dev)-2])-ord('a'))+ord("0")            #get the base letter of the /dev/sdX1 device  and convert to integer
                            x += 1                                                  #increment the dev letter integer
                        else:
                            logging.info("Space of Destination is ok for source to copy to "+zz+ext)
                            x = (ord(dev[len(dev)-2])-ord('a'))+ord("0")            #get the base letter of the /dev/sdX1 device  and convert to integer
                            x += 1                                                  #increment the dev letter integer
                            y +=1
                    if x < ord(":"):
                        z =(x-ord("0")) + ord("a")
                        dev = "/dev/sd"+chr(z)+"1"
                        while (not usb.isUsbPresent(dev)) and x< ord(':'):   #If this mount is not there then we loook further
                            z += 1                                           #Find a mount that is there
                            x += 1
                            dev = "/dev/sd"+chr(z)+"1"
                    else:
                        x = ord(":")
                        z = ord("k")

                # we think we have keys to work with if we go forward from here. where the size is ok for the copy
                z = ord("a")                                                         #Z is the ordinal value of the mount
                dev = "/dev/sda1"
                l = []
                y = [0,0,0]
                logging.info("Ready to start the copies")
                while z < ord('k'):
                    if usb.isUsbPresent(dev):		                             #we check the key to see if its mounted and present
                        y[1] = usb.getMount(dev)
                        if y[1] != "/media/usb11":
                            x = ord(y[1][len(y[1])-1])                               #X is the ord of the mount point
                        else: x = ord(':')
                        if y[1] != "" and (not os.path.isdir(y[1]+ext)):               #we don't have the desitnation path and we have a valid mount
                            os.mkdir(y[1]+ext)                                         # we make a directory
                        b = '/media/usb0'+ext
                        c = y[1]+ext
                        d = '--i '+b+' --o '+c
                        logging.info("passing: "+d)
                        try:
                            y[0] = subprocess.Popen('/usr/bin/python3 /usr/local/connectbox/battery_tool_venv/lib/python3.7/site-packages/neo_batterylevelshutdown/USBCopyUtil.py '+d, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True) # Start the copy as a subprocess
                            y[2] = y[0].pid+1
                            l.append(y)
                            logging.info("started copy from /media/usb0/source/ to "+y[1]+ext+" as pid: "+str(y[2]))
                            try:
                                out, err = y[0].communicate(input=None, timeout=2)
                                if err == '':
                                    self.display.pageStack = 'wait'
                                    self.display.showWaitPage("Copying USB"+chr(x)+"\nSize is: "+str(int(s/1000))+"MB")      #Ok we have the key started on the copy.
                                    time.sleep(3)
                                else:
                                    if y[1] == '/media/usb11':
                                       xy = ord("0")
                                    else:
                                       xy = ord(y[1][len(y[1])-1])                      #X is the ord of the mount point
                                    self.display.pageStack = 'wait'
                                    self.display.showWaitPage("Failed USB"+(chr(xy)))   #Ok we have the key removed lets move on.
                                    logging.info("Failed to start Copy Process output is "+y[1]+":"+str(err))
                                    time.sleep(3)
                            except subprocess.TimeoutExpired:
                                pass                                                    # if the program is running we don't expect to get communication.
                                                                                        #                             we assiume no news is good news.
                        except subprocess.SubprocessError:
                                # We failed to make the subdirectgory on the USB key.  Thats odd
                                logging.info("We failed to start the copy on "+y[1]+ext)
                                if y[1] == '/media/usb11/':
                                     xy = ord("0")
                                else:
                                     xy = ord(y[1][len(y[1])-1])                        #X is the ord of the mount point
                                self.display.pageStack = 'wait'
                                self.display.showWaitPage("Failed USB"+(chr(xy)))       #Ok we have the key removed lets move on.
                                time.sleep(5)
                                logging.info("Copy subprocess failed to start copy to "+str(y[1])+" kill output "+str(out)+":"+str(err))
                                y[2]=0
                                y[1]=0
                    z +=1
                    dev = '/dev/sd'+chr(z)+'1'

# Ok we started all the copies now we need to check for closure of the copy
            logging.info("Starting end of copy testing, lenth of l is "+str(len(l)))
            y=[0,0,0]
            yy = 0
            for y in l:
                try:
                    yy = y[0].poll()        #This lets check the status of the process without asking for communication.
                    if str(yy) != None:     # python keyword None would mean no return code, process still running
                        if y[1] == "/media/usb11":
                            xy = ord("0")
                        else:
                            xy = ord(y[1][len(y[1])-1])                      #X is the ord of the mount point
                        logging.info("Finished the copy of USB "+chr(xy))
                        self.display.pageStack = 'wait'
                        self.display.showWaitPage("Finished USB"+(chr(xy)))  #Ok we have the key removed lets move on.
                        usb.unmount(y[1])
                        time.sleep(3)
                    else:                                    #We are here because we are still running the copy utility
                        if y[1] == "/media/usb11":
                            xy = ord("0")
                        else:
                            xy = ord(y[1][len(y[1])-1])       #X is the ord of the mount point
                        self.display.pageStack = 'wait'
                        self.display.showWaitPage("Copying USB"+(chr(xy)+"\nSize is: "+str(s)))   #Ok we have the key removed lets move on.
                        time.sleep(3)

    #We tried to get status of the process but got an error trying.  So we have to assume its finished or bad
                except:
                    if y[1] == "/media/usb11":
                        xy = ord("0")
                    else:
                        xy = ord(y[1][len(y[1])-1])                                  #X is the ord of the mount point
                    logging.info("Finished the copy of USB "+chr(xy))
                    self.display.pageStack = 'wait'
                    self.display.showWaitPage("Finished USB"+(chr(xy)))              #Ok we have the key removed lets move on.
                    os.sync
                    usb.unmount(y[1])
                    time.sleep(3)
# end of looping to check process completion

# loop through all keys present (mounted or not) and tell user to remove them
            logging.info("All Copy processes have completed")
            os.sync()
            logging.info("Ok now we want to remove all the usb keys")
            z = ord('a')
            curDev='/dev/sda1'
            while z < ord("k"):
                if usb.isUsbPresent(curDev):
                    if usb.getMount(curDev):
                        usb.umount(usb.getMount(curDev))
                        usb.umount(curDev)
                    self.display.showRemoveUsbPage()                                      #show the remove usb page
                    self.display.pageStack = 'removeUsb'                                  #show we removed the usb key
                    self.command_to_reference = 'remove_usb'
                    time.sleep(3)                                                         #Wait a second for the removeal
                    while (usb.isUsbPresent(curDev)):
                        time.sleep(3)
                z += 1                                                                    # lets look at the next one
                curDev = '/dev/sd'+chr(z)+'1'                                             #create the next curdev
            # We finished the umounts
            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            logging.debug("Success page now deleting the PauseMount file")
            except:
                pass
            checkReturn(self, NoMountOrig)
            return


    def handleButtonPress(self, channel):
        '''
        The method was created to handle the button press event.  It will get the time buttons
        pressed and then, based upon other criteria, decide how to control further events.

        :param channel: The pin number that has been pressed and thus is registering a 0
        :return: nothing

        '''
        logging.debug("we had a button press")
        if self.display_type == 'DummyDisplay':                                           # this device has no buttons or display, skip
            return

        # this section is to prevent both buttons calling this method and getting two replies
        if self.BUTTON_PRESS_BUSY:  # if flag is set that means this method is currently being used
            logging.debug("skipping button press - BUSY flag")
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
            logging.debug("hit self.check_press_threshold_sec line 158")
            if channel == self.USABLE_BUTTONS[0]:                                           # this is the left button
                logging.info("Left button: pageStack ="+str(pageStack))
                if pageStack in ['success']:                # return to 1st page of admin stack
                    self.moveToStartPage(channel)
                elif pageStack in ['confirm', 'error']:     # return to first page admin stack
                    self.chooseCancel()
                elif pageStack in ['removeUsb']:            # never reach here... loops elsewhere until they remove the USB stick
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
            logging.debug("hit dual button press time, move forward")
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

       '''

        
        # otherChannel is the button that has not been passed in by the channel parameter.
        otherChannel = self.USABLE_BUTTONS[0] if channel == self.USABLE_BUTTONS[1] else \
            self.USABLE_BUTTONS[1]
        
        # Temporarily turn off the push button interrupt handler
        #   and turn on the push button pins as regular inputs
        # Note that this is a specific case of buttons being on PG6 and PG7... 
        #  If another implementation is made for NEO, this will need updating.
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x00777777 >/dev/null"
            os.popen(cmd).read()

         
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

        # We are through with reading of the button states so turn interrupt handling back on
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x66777777 >/dev/null"
            os.popen(cmd).read()

        return buttonTime, dualTimeRecorded

    def chooseCancel(self):
        """ method for use when cancelling a choice"""
        logging.debug("Choice cancelled")
        self.command_to_reference = ''                                                          # really don't want to leave this one loaded
        self.display.switchPages()                                                              # drops back to the admin pages
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

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
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

    def switchPages(self):
        """method for use on button press to change display options"""
        logging.debug("You have now entered, the SwitchPages")
        self.display.switchPages()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.hat.DISPLAY_TIMEOUT_SECS

    def moveToStartPage(self,channel):
        self.display.moveToStartPage()
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
