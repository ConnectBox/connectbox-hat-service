# -*- coding: utf-8 -*-

import subprocess
import shutil
import time
import logging
import os
import RPi.GPIO as GPIO  # pylint: disable=import-error
from .usb import USB
from . import page_display_image
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

            logging.info("copy from USB")
            x = ord("a")
            while(not usb.isUsbPresent('/dev/sd'+chr(x)+"1") and x < ord("k")):    # check to see if usb is inserted
                x += 1
            if x == ord("k"):
                self.display.showNoUsbPage()                # if not, alert as this is required
                self.display.pageStack = 'error'
                return                                      # cycle back to menu
            dev = '/dev/sd'+chr(x)+'1'
            with open('/usr/local/connectbox/PauseMount','w') as fp:
                fp.write(" ")
            time.sleep(2)
            self.pageStack = 'wait'                         # Dont allow the display to turn off
            logging.info("Using location "+dev+" as media copy location")
            if usb.getMount(dev) == '/media/usb0':
                logging.info("Moving /media/usb0 to /media/usb11  be able to copy")
                if not os.path.exists('/media/usb11'):      # check that usb11 exsists to be able to move the mount
                    os.mkdir('/media/usb11')                # make the directory
                if not usb.moveMount(usb.getDev(dev), dev, '/media/usb11'): # see if our remount was successful
                    self.display.showErrorPage()            # if not generate error page and exit
                    self.display.pageStack = 'error'
                    try: os.remove('/usr/local/connectbox/PauseMount')
                    except:
                        pass
                    return
            logging.info("Preparing to check space of source "+(usb.getMount(dev)))
            (d,s) = usb.checkSpace(usb.getMount(dev))       # verify that source is smaller than destination
            logging.info("space checked source : "+str(s)+", destination : "+str(d)+" device "+dev)
            if s > d:
                logging.info("There is not enough space we will call an error on "+dev)
                self.display.showNoSpacePage(1, dev )       # if not, alert as this is a problem
                self.display.pageStack ='error'
                if usb.getMount(dev) == '/media/usb11':
                    logging.info("since we moved the moount we want /media/usb0 back")
                    usb.moveMount(dev, '/media/usb11', '/media/usb0')
                    try: os.remove('/media/usb11')
                    except:
                        pass
                try: os.remove('/usr/local/connectbox/PauseMount')
                except:
                    pass
                return
            a = usb.getMount(dev)
            logging.info("starting to do the copy with device "+a)
            if not usb.copyFiles(a):                         # see if we copied successfully
                logging.info("failed the copy. display an error page")
                self.display.showErrorPage()                # if not generate error page and exit
                self.display.pageStack = 'error'
                try: os.remove('/usr/local/connectbox/PauseMount')
                except:
                    pass
                return
            logging.info("Finished all usb keys")
            logging.info("Ok now we want to remove all the usb keys")
            curDev='/dev/sda1'
            x = ord('a')
            while (not usb.isUsbPresent(curDev)) and x < ord("k"):
                logging.info("is key "+curDev+" present? "+str(usb.isUsbPresent(curDev))) 
                x +=1
                curDev = '/dev/sd'+chr(x)+'1'

            while usb.isUsbPresent(curDev) and x < ord("k"):
                self.display.showRemoveUsbPage()        #show the remove usb page
                self.display.pageStack = 'removeUsb'    #show we removed the usb key
                self.command_to_reference = 'remove_usb'
                time.sleep(1)                           #Wait a second for the removeal
                while (not usb.isUsbPresent(curDev)) and x < ord("k"):
                    x += 1                              # lets look at the next one
                    curDev = '/dev/sd'+chr(x)+'1'       #create the next curdev
            # We finished the umounts
            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            logging.info("Success page now deleting the PauseMount file")
            try: os.remove('/usr/local/connectbox/PauseMount')
            except:
                pass 
            self.display.pageStack = 'success'              # if the usb was removed
            self.display.showSuccessPage()                  # display success page
            os.sync()
            return

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


        elif command == 'copy_to_usb':
            logging.info("got to copy to usb code")
            self.display.showConfirmPage()                     #We found at least one key
            x = ord('a')
            dev = '/dev/sd'+chr(x)+'1'
            self.display.showInsertUsbPage()                    #tell them to inert new keys
            while (not usb.isUsbPresent(dev)) and x < ord('k'):
                x += 1
                dev = '/dev/sd'+chr(x)+'1'
                if x == ord('k'):
                    x = ord('a')
                    dev = '/dev/sd'+chr(x)+'1'
            self.display.pageStack = 'confirm'
            self.display.showConfirmPage()
            time.sleep(3)
            with open('/usr/local/connectbox/PauseMount','w') as fp:
                pass
            fp.close()
            time.sleep(2)
            self.display.pageStack = 'wait'
            self.display.showWaitPage()
            logging.info("we have found at least one usb to copy to: "+dev)
            x = ord('a')
            dev ='/dev/sd'+chr(x)+'1'
            y = 0
            logging.info("were ready to start size check")

            while x < ord('k'):
                if usb.getMount(dev) == '/media/usb0':             # if the key is mounted on '/media/usb0' then we have to move it.
                    logging.info("Moving /media/usb0 to /media/usb11 be able to copy")
                    y += 1
                    if not os.path.exists('/media/usb11'):         # check that usb11 exsists to be able to move the mount
                        os.mkdir('/media/usb11')                   # make the directory
                    if not usb.moveMount( dev, '/media/usb0', '/media/usb11'): # see if our remount was successful
                        self.display.showErrorPage()               # if not generate error page and exit
                        self.display.pageStack = 'error'
                        try: os.remove('/usr/local/connectbox/PauseMount')
                        except:
                            pass
                        return
                if usb.getMount(dev) != "": y += 1
                x += 1
                dev = '/dev/sd'+chr(x)+'1'

            x = ord('a') 
            dev = '/dev/sd'+chr(x)+'1'
            while x < ord('k') and y > 0:                          #While we know we have a usb key lets check the sizes
                if usb.getMount(dev) != "":
                    zz = usb.getMount(dev)
                    logging.info("getting the size for source /media/usb0 and destination "+zz)
                    (d,s) = usb.checkSpace('/media/usb0', zz)       # verify that source is smaller than destination
                    logging.info("Space of Destination  is : "+str(d)+" , Source: "+str(s)+" at: "+dev)
                    if d<s:                                        #if destination free is less than source we don't have enough space
                        logging.info("source exceeds destination at"+zz)
                        y -= 1
                        while usb.isUsbPresent(dev):
                            logging.info("we found we don't have enough sapce on usb key "+dev)
                            self.display.showNoSpacePage(2, dev )       #alert that there is a problem
                            self.display.pageStack = 'remove_usb'       #remove this usb
                            self.command_to_reference = 'remove_usb'    #let execute commands know what we want
                            time.sleep(1)                               #wait a second
                        usb.unmount(zz)                                 #Make sure we unmount that device.
                        usb.unmount(dev)                                #Make sure we unmount the mount point
                        if zz[len(zz)-1] != '0':                          # as long as its not /media/usb0
                            os.system('rm -r '+ z)                      #Make sure we remove that directory since PauseMount is set
                    else: logging.info("Space of Desitinationis ok for source to copy to "+zz)
                    x+= 1
                else:                                                   #we have a key but it is not mounted
                    if usb.isUsbPresent(dev):                           #Hmm USB is present but not mounted.
                        z = ord(dev[len(dev)-2])-ord('a')               #get the base number of the /dev/sdX1 device that it should be not the ordinate
                        if z == 0:
                            z == ord('1')                               #I don't want to mount as usb0
                        else:
                            z += ord('0')
                        while usb.isUsbPresent('/media/usb'+chr(z)) and z< ord(':'):
                            z += 1                                      #Find a mount that isn't there
                        if z < ord(':'):
                            os.system('mkdir /media/usb'+chr(z))        #Make the directory
                            if (not usb.mount(dev, '/media/usb'+chr(z))):
                                self.disiplay.showErrorPage()
                                self.display.pageStack = 'error'
                                try: os.remove('/usr/local/connectbox/PauseMount')
                                except:
                                   pass
                                return
                            x -= 1						#decrement so we can recheck this mount
                        else:
                                self.disiplay.showErrorPage()
                                self.display.pageStack = 'error'
                                try: os.remove('/usr/local/connectbox/PauseMount')
                                except:
                                   pass
                                return
                x += 1;
                dev = '/dev/sd'+chr(x)+'1'
            logging.info("we passed size checks so we are going on to copy now")


            # we think we have keys to work with if we go forward from here.

            self.display.showWaitPage()
            x = ord('a')
            dev = '/dev/sd'+chr(x)+"1"
            while x < ord('k'):
                if usb.isUsbPresent(dev):		             #find the first usb key
                    logging.info("try copying to "+dev+" at location: "+usb.getMount(dev)+" from '/media/usb0'")
                    if not usb.copyFiles('/media/usb0', usb.getMount(dev)): # see if we copied successfully
                        self.display.showErrorPage()                      # if not generate error page and exit
                        self.display.pageStack = 'error'
                        logging.info("ok we failed to copy to "+dev+" at mount point "+(usb.getMount(dev)))
                        if usb.isUsbPresent('/media/usb11') and usb.getMount(usb.getDev('/media/usb11')) == '/media/usb11':
                            os.command('unmount '+usb.getDev('/media/usb11'))
                            os.command('unmount /media/usb11')
                            os.command('rmdir -f /media/usb11') 
                            logging.info("we failed on the move of /media/usb11 -> /media/usb0")
                            self.disiplay.showErrorPage()
                            self.display.pageStack = 'error'
                            try: os.remove('/usr/local/connectbox/PauseMount')
                            except:
                                pass
                            return
                        logging.info("we failed on the USB11 deletion")
                        self.disiplay.showErrorPage()
                        self.display.pageStack = 'error'
                        try: os.remove('/usr/local/connectbox/PauseMount')
                        except:
                            pass
                        return
                    else:
                        logging.info("we suceeded in copying to device"+dev)
                        x +=1
                        dev = '/dev/sd'+chr(x)+'1'
                        while x < ord('k') and not usb.isUsbPresneet(dev): #find next key or hit end.
                            x += 1
                            dev = '/dev/sd'+chr(x)+'1'
            os.sync()
            logging.info("Ok now we want to remove all the usb keys")
            curDev='/dev/sda1'
            x = ord('a')
            while (not usb.isUsbPresent(curDev)) and x < ord("k"):
                logging.info("is key "+curDev+" is not present? ")
                x +=1
                curDev = '/dev/sd'+chr(x)+'1'
            logging.info("copy done removing key at /dev/sd"+chr(x)+'1')
            try: os.remove('/usr/local/connectbox/PauseMount')
            except:
                pass 
            while usb.isUsbPresent(curDev) and x < ord("k"):
                self.display.showRemoveUsbPage()        #show the remove usb page
                self.display.pageStack = 'removeUsb'    #show we removed the usb key
                self.command_to_reference = 'remove_usb'
                time.sleep(1)                           #Wait a second for the removeal
                if not usb.isUsbPreseent(curDev):
                    x = ord('a')                        # get the current device ord
                    curDev = '/dev/sd'+chr(x)+'1'
                    while (not usb.isUSBPresent(curDev)) and x < ord("k"):
                        x += 1                          # lets look at the next one
                        curDev = '/dev/sd'+chr(x)+'1'   #create the next curdev
            # We finished the umounts
            self.display.pageStack = 'success'
            self.display.showSuccessPage()
            logging.info("finished copy to usb function")
            return 

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
            logging.debug("skipping button press - BUSY flag")
            return  # skip

        # check the amount of time that has passed since this function has been cleared and
        #  see if it exceeds the timeout set.  This avoids buttons bouncing triggering
        #  this function
        if time.time() - self.BUTTON_PRESS_CLEARED_TIME > self.BUTTON_PRESS_TIMEOUT_SEC:
            self.BUTTON_PRESS_BUSY = True  # if enough time, proceed and set the BUSY flag

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
        startTime = time.time()     # time original button is pushed
        dualStartTime = time.time() # time both buttons were pushed.
        dualTimeRecorded = 0        # to prevent time being reset when letting off of buttons

        while GPIO.input(channel) == 0:         # While original button is being pressed
            if GPIO.input(otherChannel) == 0:   # capture hold time if 2nd button down
                dualButtonTime = time.time() - dualStartTime # How long were both buttons down?
                if dualButtonTime > dualTimeRecorded:
                    dualTimeRecorded = dualButtonTime
            if GPIO.input(otherChannel) == 1:   # move start time up if not pressing other button     
                dualStartTime = time.time()     # reset start time to now
            if (time.time() - startTime) > 5:   # don't stick in this interrupt service forever
                break    

        buttonTime = time.time() - startTime    # How long was the original button down?

        # We are through with reading of the button states so turn interrupt handling back on
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c208d8 w 0x66777777 >/dev/null"
            os.popen(cmd).read()

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
