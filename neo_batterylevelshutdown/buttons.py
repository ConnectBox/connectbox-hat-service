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

            logging.debug("copy from USB")
            x = ord("a")
            while(not usb.isUsbPresent('/dev/sd'+chr(x)+"1") and x < ord("k")): # check to see if usb is inserted
                x += 1
            if x == ord("k"):
                self.display.showNoUsbPage()                                    # if not, alert as this is required
                self.display.pageStack = 'error'
                return                                                          # cycle back to menu
            dev = '/dev/sd'+chr(x)+'1'
            with open('/usr/local/connectbox/PauseMount','w') as fp:
                fp.write(" ")
                fp.close()
            time.sleep(2)
            self.pageStack = 'wait'                                             # Dont allow the display to turn off
            self.display.showWaitPage("Checking Space")
            logging.debug("Using location "+dev+" as media copy location")
            if usb.getMount(dev) == '/media/usb0':
                logging.debug("Moving /media/usb0 to /media/usb11 to be able to copy")
                if not os.path.exists('/media/usb11'):                          # check that usb11 exsists to be able to move the mount
                    os.mkdir('/media/usb11')                                    # make the directory
                if not usb.moveMount(usb.getDev(dev), dev, '/media/usb11'):     # see if our remount was successful
                    self.display.showErrorPage("Moving Mount")                  # if not generate error page and exit
                    self.display.pageStack = 'error'
                    try: os.remove('/usr/local/connectbox/PauseMount')
                    except:
                        pass
                    return
            logging.debug("Preparing to check space of source "+(usb.getMount(dev)))
            self.display.showWaitPage("Checking Space "+str(dev))
            (d,s) = usb.checkSpace(usb.getMount(dev))                           # verify that source is smaller than destination
            logging.debug("space checked source : "+str(s)+", destination : "+str(d)+" device "+dev)
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
                try: os.remove('/usr/local/connectbox/PauseMount')
                except:
                    pass
                return
            a = usb.getMount(dev)
            logging.debug("starting to do the copy with device "+a)
            self.display.showWaitPage("Copying Files "+str(dev)+"\nSize is: "+str(s))
            if not usb.copyFiles(a, "/media/usb0"):                             # see if we copied successfully
                logging.debug("failed the copy. display an error page")
                self.display.showErrorPage("Failed Copy")                       # if not generate error page and exit
                self.display.pageStack = 'error'
                if usb.getMount(dev) == '/media/usb11' :
                    logging.debug("since we moved the mount we want /media/usb0 back")
                    usb.moveMount(dev, "/media/usb11", "/media/usb0")
                    try: os.rmdir('/media/usb11')
                    except:
                        pass
                try: os.remove('/usr/local/connectbox/PauseMount')
                except:
                    pass
                return
            logging.debug("Finished all usb keys")
            logging.debug("Ok now we want to remove all the usb keys")
            curDev='/dev/sda1'
            x = ord('a')
            while (not usb.isUsbPresent(curDev)) and x < ord("k"):
                logging.debug("is key "+curDev+" present? "+str(usb.isUsbPresent(curDev))) 
                x +=1
                curDev = '/dev/sd'+chr(x)+'1'

            while usb.isUsbPresent(curDev) and x < ord("k"):
                self.display.showRemoveUsbPage("USB "+str(curDev))              #show the remove usb page
                self.display.pageStack = 'removeUsb'                            #show we removed the usb key
                self.command_to_reference = 'remove_usb'
                time.sleep(1)                                                   #Wait a second for the removeal
                while (not usb.isUsbPresent(curDev)) and x < ord("k"):
                    x += 1                                                      # lets look at the next one
                    curDev = '/dev/sd'+chr(x)+'1'                               #create the next curdev
            # We finished the umounts
            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            logging.debug("Success page now deleting the PauseMount file")
            try: os.remove('/usr/local/connectbox/PauseMount')
            except:
                pass
            self.display.pageStack = 'success'                                     # if the usb was removed
            self.display.showSuccessPage()                                         # display success page
            os.sync()
            return

        elif command == 'erase_folder':
            file_exists = False  # in regards to README.txt file
            if usb.isUsbPresent():
                self.display.pageStack = 'error'
                self.display.showRemoveUsbPage()
                return
#            if os.path.isfile('/media/usb0/README.txt'):                           # keep the default README if possible
#                file_exists = True
#                subprocess.call(['cp', '/media/usb0/README.txt', '/tmp/README.txt'])
#                logging.debug("README.txt moved")
            for file_object in os.listdir('/media/usb0'):
                file_object_path = os.path.join('/media/usb0', file_object)
                if os.path.isfile(file_object_path):
                    os.unlink(file_object_path)
                else:
                    shutil.rmtree(file_object_path)
            logging.debug("FILES NUKED!!!")
#            if file_exists:
#                subprocess.call(['mv', '/tmp/README.txt', '/media/usb0/README.txt'])  # move back
#                logging.debug("README.txt returned")
#            logging.debug("Life is good!")
            self.display.pageStack = 'success'
            self.display.showSuccessPage()


        elif command == 'copy_to_usb':
            logging.debug("got to copy to usb code")
            y = 0                                                                   # y keeps track of the number of USB keys
            z = ord('a')                                                            # Z is the ordinal of the USB key in DEV
            dev = '/dev/sd'+chr(z)+'1'                                              # X is the ordinal of the  mount point
            self.display.showInsertUsbPage()                                        #tell them to inert new keys
            while (not usb.isUsbPresent(dev)) and z < ord('k'):
                z += 1
                dev = '/dev/sd'+chr(z)+'1'
                if z == ord('k'):
                    z = ord('a')
                    dev = '/dev/sd'+chr(z)+'1'
            if z < ord('k'):
                self.display.pageStack = 'confirm'
                self.display.showConfirmPage()
                time.sleep(1)
            with open('/usr/local/connectbox/PauseMount','w') as fp:
                pass
            fp.close()
            time.sleep(2)

            self.display.pageStack = 'wait'
            self.display.showWaitPage("Checking Sizes")

            logging.debug("we have found at least one usb to copy to: "+dev)
            y = 0
            logging.debug("were ready to start size check")
            a = "/content/"
            while z < ord('k'):
                if usb.getMount(dev) == '/media/usb0':                              # if the key is mounted on '/media/usb0' then we have to move it.
                    logging.debug("Moving /media/usb0 to /media/usb11 be able to copy")
                    if not os.path.exists('/media/usb11'):                          # check that usb11 exsists to be able to move the mount
                        os.mkdir('/media/usb11')                                    # make the directory
                    if not usb.moveMount( dev, '/media/usb0', '/media/usb11'):      # see if our remount was successful
                        self.display.showErrorPage("Moving Mount")                  # if not generate error page and exit
                        self.display.pageStack = 'error mounting'
                        os.rmdir("/media/usb11")
                        try: os.remove('/usr/local/connectbox/PauseMount')
                        except:
                            pass
                        return

                if usb.getMount(dev) != "": y += 1

                while z < ord('k') and y > 0:                                       #While we know we have a usb key lets check the sizes
                    zz = usb.getMount(dev)
                    if zz != "":
                        logging.debug("getting the size for source /media/usb0 and destination "+zz)
                        if os.path.isdir(zz+a):
                            try:
                                shutil.rmtree((zz+a), ignore_errors=True)
                            except OSError:
                                logging.info("had a problem deleting the destination file: ",zz+a)
                                return
                        (d,s) = usb.checkSpace(('/media/usb0'), zz)                 # verify that source is smaller than destination
                        logging.debug("Space of Destination  is : "+str(d)+" , Source: "+str(s)+" at: "+dev)
                        if d<s or s==0:                                             #if destination free is less than source we don't have enough space
                            if d<s: logging.info("source exceeds destination at"+zz)
                            else: logging.info("source is 0 bytes in length so nothing to copy")
                            y -= 1
                            while usb.isUsbPresent(dev):
                                logging.info("we found we don't have enough sapce on usb key "+dev)
                                if d<s:
                                    self.display.showNoSpacePage(2, dev )           #alert that there is a problem
                                    os.sync
                                else: self.display.showNoSpacePage(2,"No Source Files")
                                time.sleep(3)
                                self.display.pageStack = 'remove_usb'               #remove this usb
                                self.command_to_reference = 'remove_usb'            #let execute commands know what we want
                                time.sleep(4)                                       #wait a second
                            usb.unmount(zz)                                         #Make sure we unmount that device.
                            usb.unmount(dev)                                        #Make sure we unmount the mount point
                            if zz[len(zz)-1] != '0':                                # as long as its not /media/usb0
                                os.system('rm -r '+ zz)                             #Make sure we remove that directory since PauseMount is set
                            self.display.pageStack = 'wait'
                            self.display.showWaitPage("Checking Sizes")             #Ok we have the key removed lets move on.
                        else:
                            logging.debug("Space of Desitinationis ok for source to copy to "+zz)
                            x = (ord(dev[len(dev)-2])-ord('a'))+ord("0")            #get the base letter of the /dev/sdX1 device  and convert to integer
                            x += 1                                                  #increment the dev letter integer
                            if x < ord(":"):
                                z =(x-ord("0")) + ord("a")
                                dev = "/dev/sd"+chr(z)+"1"
                                while (not usb.isUsbPresent(dev)) and x< ord(':'):
                                    z += 1                                           #Find a mount that isn't there
                                    x += 1
                                    dev = "/dev/sd"+chr(z)+"1"
                            else:
                                x = ord(":")
                                z = ord("k")
                    else:                                                           #we have a key but it is not mounted so we do nothing as we rely on PxUSBm.py to do the mounting
                        pass

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
                        try: shutil.rmtree(y[1]+a)                                   #make sure there isn't an exsisting /source/ directory
                        except:
                            pass
                        if y[1] != "" and (not os.path.isdir(y[1]+a)):               #we don't have the desitnation path and we have a valid mount
                            os.mkdir(y[1]+a)                                         # we make a directory
                        b = '/media/usb0'+a
                        c = y[1]+a
                        d = '--i '+b+' --o '+c
                        logging.info("passing: "+d)
                        try:
                            y[0] = subprocess.Popen('/usr/bin/python3 /usr/local/connectbox/battery_tool_venv/lib/python3.7/site-packages/neo_batterylevelshutdown/USBCopyUtil.py '+d, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True) # Start the copy as a subprocess
                            y[2] = y[0].pid+1
                            l.append(y)
                            logging.info("started copy from /media/usb0/* to "+y[1]+" as pid: "+str(y[2]))
                            try:
                                out, err = y[0].communicate(input=None, timeout=2)
                                if err == None:
                                    l.append(y)
                                    self.display.pageStack = 'wait'
                                    self.display.showWaitPage("Copying USB"+chr(x)+"\nSize is: "+str(s))      #Ok we have the key started on the copy.
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
                                logging.info("We failed to start the copy on "+y[1]+a)
                                if y[1] == '/media/usb11/':
                                     xy = ord("0")
                                else:
                                     xy = ord(y[1][len(y[1])-1])                        #X is the ord of the mount point
                                self.display.pageStack = 'wait'
                                self.display.showWaitPage("Failed USB"+(chr(xy)))       #Ok we have the key removed lets move on.
                                time.sleep(5)
                                logging.info("Copy subprocess fialed to start copy to "+str(y[1])+" kill output "+str(out)+":"+str(err))
                                y[2]=0
                                y[1]=0
                    z +=1
                    dev = '/dev/sd'+chr(z)+'1'

            # Ok we started all the copyies now we need to check for closure of the copy
            logging.info("Starting end of copy testing, lenth of l is "+str(len(l)))
            y=[0,0,0]
            yy = 0
            x = 0
            xx = len(l)
            while x < xx:                                                                #We look at all processes we started till we have none.
                for y in l:
                    try:
                        yy = y[0].poll()                                                 #This lets check the status of the process without asking for communication.
                        if str(yy) != "None":
                            try:
                                out, err = y[0].communicate(input=None, timeout=3)       #We do the communicate in case there is pending IO that might put the process in the wait state.
                                if out == 0 and err == 0:
                                    if y[1] == "/media/usb11/":
                                        xy = ord("0")
                                    else:
                                        xy = ord(y[1][len(y[1])-1])                      #X is the ord of the mount point
                                    logging.info("Finished the copy of USB "+chr(xy))
                                    self.display.pageStack = 'wait'
                                    self.display.showWaitPage("Finished USB"+(chr(xy)))  #Ok we have the key removed lets move on.
                                    usb.unmount(y[1])
                                    dev = usb.getDev(y[1])
                                    usb.unmount(dev)
                                    time.sleep(3)
                                    y[2]=0
                                    l.remove(x)
                                    xx -= 1                                              #We have removed a list element so decrement the total count and current position
                                    x -= 1

                                else:
                                    if err == 0:
                                        if y[1] == "/media/usb11/":
                                            xy = ord("0")
                                        else:
                                            xy = ord(y[1][len(y[1])-1])                  #X is the ord of the mount point
                                        logging.info("Were not sure what happened with the copy of the USB "+chr(xy))
                                        self.display.pageStack = 'wait'
                                        self.display.showWaitPage("Copying USB"+(chr(xy)))
                                        time.sleep(2)
                                    else:
                                        if y[1] ==  "/media/usb11/":
                                            xy = ord("0")
                                        else:
                                            xy = ord(y[1][len(y[1])-1])                 #X is the ord of the mount point
                                            logging.info("Copy Errored out USB "+y[1]+" with error "+str(out)+":"+str(err))
                                            self.display.pageStack = 'wait'
                                            self.display.showWaitPage("Failed USB"+(chr(xy)))              #Ok we have the key removed lets move on.
                                            os.sync
                                            dev = usb.getDev(y[1])
                                            usb.unmount(y[1])
                                            usb.unmount(dev)
                                            l.remove(x)
                                            time.sleep(3)
                                            xx -= 1                                     #We have removed a list element so decrement the total count and current position
                                            x -= 1

                            except subprocess.TimeoutExpired:
#                            We expected to get some output status since the poll was not nul but we timed out
                                if y[1] == "/media/usb11":
                                    xy = ord("0")
                                else:
                                    xy = ord(y[1][len(y[1])-1])                         #X is the ord of the mount point
                                logging.info("Finished the copy of USB "+chr(xy))
                                self.display.pageStack = 'wait'
                                self.display.showWaitPage("Finished USB"+(chr(xy)))     #Ok we have the key removed lets move on.
                                os.sync
                                dev = usb.getDev(y[1])
                                usb.unmount(y[1])
                                usb.unmount(dev)
                                time.sleep(3)
                                y[2]=0
                                l.remove(x)
                                xx -= 1                                                 #We have removed a list element so decrement the total count and current position
                                x -= 1
                        else:                                                           #We are here because we are still running the copy utility
                            if y[1] == "/media/usb11":
                                xy = ord("0")
                            else:
                                xy = ord(y[1][len(y[1])-1])                             #X is the ord of the mount point
                            self.display.pageStack = 'wait'
                            self.display.showWaitPage("Copying USB"+(chr(xy)+"\nSize is: "+str(s)))           #Ok we have the key removed lets move on.
                            time.sleep(3)
                    except:
                    #We tried to ge status of the process but got an error trying.  So we have to assume its finished or bad
                        if y[1] == "/media/usb11/":
                            xy = ord("0")
                        else:
                            xy = ord(y[1][len(y[1])-1])                                  #X is the ord of the mount point
                        logging.info("Finished the copy of USB "+chr(xy))
                        self.display.pageStack = 'wait'
                        self.display.showWaitPage("Finished USB"+(chr(xy)))              #Ok we have the key removed lets move on.
                        os.sync
                        dev = usb.getDev(y[1])
                        usb.unmount(y[1])
                        usb.unmount(dev)
                        time.sleep(3)
                        y[2]=0
                        l.remove(x)
                        xx -= 1                                                           #We have removed a list element so decrement the total count and current position
                        x -= 1
                    x += 1                                                                #were at the end of the for loop we need to increment our list counter

                x = 1                                                                     #Were at the end of the while loop, We finished looking at all processes now we start over
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
            self.display.showSuccessPage("Copy Complete")
            logging.debug("Success page now deleting the PauseMount file")
            try: os.remove('/usr/local/connectbox/PauseMount')
            except:
                pass
            os.sync()
            return


    def handleButtonPress(self, channel):
        '''
        The method was created to handle the button press event.  It will get the time buttons
        pressed and then, based upon other criteria, decide how to control further events.

        :param channel: The pin number that has been pressed and thus is registering a 0
        :return: nothing

        '''
        logging.info("we had a button press")
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

        logging.info("Handling button press")
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
                if pageStack in ['confirm', 'error', 'success']:                            # return to admin stack
                    self.chooseCancel()
                elif pageStack in ['removeUsb']:                                            # gonna keep going until they remove the USB stick
                    self.chooseEnter(pageStack)
                else:                                                                       # anything else, we treat as a moveForward (default) function
                    self.moveForward(channel)
            else:                                                                           # right button
                if pageStack == 'status':                                                   # standard behavior
                    self.moveBackward(channel)
                elif pageStack in ['error', 'success']:                                     # both conditions return to admin stack
                    self.chooseCancel()
                else:                                                                       # this is an enter key
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
            if (time.time() - startTime) > 5:                                                   # don't stick in this interrupt service forever
                break    

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
                self.display.showConfirmPage()
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
