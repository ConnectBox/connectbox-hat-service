#! -*- coding: utf-8 -*-

import logging
import os
import threading
import time
from PIL import Image


from HAT_Utilities import *
import page_none
import page_main

from globals import *
import hats as hat

#from . import page_mainA
import neo_batterylevelshutdown.page_battery as page_battery
import neo_batterylevelshutdown.page_info as page_info
import neo_batterylevelshutdown.page_stats as page_stats
import neo_batterylevelshutdown.page_memory as page_memory
import neo_batterylevelshutdown.page_battery_low as page_battery_low
import neo_batterylevelshutdown.page_power_down as page_power_down
import neo_batterylevelshutdown.page_display_image as page_display_image
import neo_batterylevelshutdown.page_multi_bat as page_multi_bat
#from . import page_waiting




class DummyDisplay:

    # pylint: disable=unused-argument
    # This is a standard interface - it's ok not to use the argument
    def __init__(self, hat_class):
        self.display_type = 'DummyDisplay'

    def moveForward(self):
        pass

    def moveBackward(self):
        pass

    def powerOffDisplay(self):
        pass

    def showLowBatteryWarning(self):
        pass

    def hideLowBatteryWarning(self):
        pass

    def drawLogo(self):
        # should this be exposed publicly, or should it be private and
        #  simply called in the constructor or via some standard interface?
        pass


# pylint: disable=too-many-instance-attributes
class OLED:

    # What to show after startup and blank screen
    STARTING_PAGE_INDEX = 0  # the main page

    def __init__(self, hat_class):
        logging.info("In __init__ of OLED")
        self.hat = hat_class
        # rename this.... perhaps it doesn't even need to be stored
        self.axp = self.hat.axp   # powerManagementDevice
        self.display_type = 'OLED'
        self.display_device = get_device()
        self.blank_page = page_none.PageBlank(self.display_device)
        self.low_battery_page = \
            page_battery_low.PageBatteryLow(self.display_device)
        self.power_down_page = \
            page_power_down.PagePowerDown(self.display_device)
        self.statusPages = [
            page_main.PageMain(self.display_device, self.axp),
            page_info.PageInfo(self.display_device),
            page_battery.PageBattery(self.display_device, self.axp),
            page_multi_bat.PageMulti_Bat(self.display_device, self.axp),
            page_memory.PageMemory(self.display_device),
            page_stats.PageStats(self.display_device, 'hour', 1),
            page_stats.PageStats(self.display_device, 'hour', 2),
            page_stats.PageStats(self.display_device, 'day', 1),
            page_stats.PageStats(self.display_device, 'day', 2),
            page_stats.PageStats(self.display_device, 'week', 1),
            page_stats.PageStats(self.display_device, 'week', 2),
            page_stats.PageStats(self.display_device, 'month', 1),
            page_stats.PageStats(self.display_device, 'month', 2),
            page_display_image.PageDisplayImage(self.display_device, 'show_admin.png'),
        ]
        self.adminPages = [
            page_display_image.PageDisplayImage(self.display_device, 'copy_from_usb.png'),
            page_display_image.PageDisplayImage(self.display_device, 'erase_folder.png'),
            page_display_image.PageDisplayImage(self.display_device, 'copy_to_usb.png'),
            page_display_image.PageDisplayImage(self.display_device, 'exit.png')             #must be last
        ]
        self.adminPageNames = [
            'copy_from_usb',
            'erase_folder',
            'copy_to_usb',
            'exit'
        ]

        self.pages = self.statusPages
        self.pageStack = 'status'
        DISPLAY_TIMEOUT_SECS=120
        hat.displayPowerOffTime = time.time() + DISPLAY_TIMEOUT_SECS  # reset
        self._curPage = self.pages[self.STARTING_PAGE_INDEX]
        # callbacks run in another thread, so we need to lock access to the
        #  current page variable as it can be modified from the main loop
        #  and from callbacks
        self._curPageLock = threading.Lock()
        # draw the Brand logo - classes containing an OLED display
        #  manage timeouts and timed display power-downs, so we leave that
        #  as an exercise for anyone using this class
        self.drawLogo()
        time.sleep(3)       # display logo screen for 3 seconds

    def getAdminPageName(self):
        return self.adminPageNames[self.adminPages.index(self._curPage)]

    def checkIfLastPage(self):
        return self._curPage == self.pages[-1]

    def showRemoveUsbPage(self,a=''):
        with self._curPageLock:
            logging.debug("Showing remove usb page")
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'remove_usb.png',a)
            self._curPage.draw_page()

    def showInsertUsbPage(self):
        with self._curPageLock:
            logging.debug("Showing insert usb page")
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'insert_usb_key.png')
            self._curPage.draw_page()


    def showNoUsbPage(self):
        with self._curPageLock:
            logging.debug("Showing no usb page")
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'error_no_usb.png')
            self._curPage.draw_page()

    def showNoSpacePage(self,a,b):
        with self._curPageLock:
            logging.debug("Showing no space page")
            if a == 1: self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'error_no_space.png',b)
            else: self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'error_no_space2.png',b)

            self._curPage.draw_page()

    def showWaitPage(self,b=''):
        global sequence
        global sequence_time
        global a
        print ("show wait page value b is: "+str(b)+" sequence is "+str(int(sequence)))
        with self._curPageLock:
            logging.debug("Showing wait page "+ str(sequence) + " " +str(b) + "time: " + str(time.time() - sequence_time))
            if (time.time() - sequence_time) >= 1.0:
                sequence = ((sequence + 1.0) % 7)
                sequence_time = time.time()
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                ('wait-' + str(int(sequence)) + '.png'),b)
            a = b
            self._curPage.draw_page()

    def showConfirmPage(self):
        with self._curPageLock:
            logging.debug("Showing confirm choice page")
            self.pageStack = 'confirm'
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'confirm.png')
            self._curPage.draw_page()

    def showSuccessPage(self):
        with self._curPageLock:
            logging.debug("Showing success page")
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'success.png')
            self._curPage.draw_page()

    def showErrorPage(self,b=""):
        with self._curPageLock:
            logging.debug("Showing error page")
            self._curPage = page_display_image.PageDisplayImage(self.display_device,
                                                                'error.png',b)

            self._curPage.draw_page()

    def switchPages(self):
        '''

        This method is to switch between the original stack of pages referred to as status pages
        and the new stack of pages referred to as admin pages.  This is based upon the variable
        pageStack.

        :return: Nothing
        '''

        # First check to make sure the admin page stack is allowed...
        #  The last page in the normal stack is the admin page so we can simply
        #  test if the screen_enable[lastPage] is '0' and bail out in that case
        screenList = screen_enable
        adminPage = len(self.statusPages) - 1       # globals.screen_enable maps statusPages onlu
        if screenList[adminPage] == 0:
            return

        with self._curPageLock:

            self.pages = self.statusPages if self.pageStack == 'admin' else self.adminPages
            self.pageStack = 'status' if self.pageStack == 'admin' else 'admin'
            logging.debug("Current page stack: %s", self.pageStack)
            self._curPage = self.pages[0]

            # draw the page while holding the lock, so that it doesn't change
            #  underneath us
            self._curPage.draw_page()
            logging.debug("Transitioned to page %s", self._curPage)


    def moveToStartPage(self):
        with self._curPageLock:
            self._curPage = self.pages[self.STARTING_PAGE_INDEX]
            self.pageStack = 'admin'
            self._curPage.draw_page()


    def moveForward(self):
        with self._curPageLock:
            logging.debug("Current page is %s", self._curPage)
            if self._curPage not in self.pages:
                # Always start with the starting page if the screen went off
                #  or if we were showing the low battery page
                self._curPage = self.pages[self.STARTING_PAGE_INDEX]

            #need to handle both admin and status page stacks!
            else:
                # Figure out what the index of the next valid page

                current_page_index = self.pages.index(self._curPage)
                page_count = len(self.pages)
                next_page_index = (current_page_index +1) % page_count
                if self.pages == self.statusPages:      # we are in the status pages stack
                    screenList = screen_enable          # valid only for status pages... not admi
                    while screenList[next_page_index % page_count] == 0:
                        next_page_index = (next_page_index+1) % page_count   # skip page with value of
                self._curPage = \
                        self.pages[next_page_index]

            # draw the page while holding the lock, so that it doesn't change
            #  underneath us
            self._curPage.draw_page()
            logging.debug("Transitioned to page %s", self._curPage)

    def moveBackward(self):
        with self._curPageLock:
            logging.debug("Current page is %s", self._curPage)
            if self._curPage not in self.pages:
                # Always start with the starting page if the screen went off
                #  or if we were showing the low battery page
                self._curPage = self.pages[self.STARTING_PAGE_INDEX]
            else:
                # move backwards in the page list
                # Figure out what the index of the next valid page
                screenList = screen_enable
                current_page_index = self.pages.index(self._curPage)
                page_count = len(self.pages)
                next_page_index = (current_page_index + page_count -1) % page_count
                while screenList[next_page_index % page_count] == 0:
                    next_page_index = (next_page_index + page_count -1) % page_count   # skip page with value 0  
                self._curPage = \
                        self.pages[next_page_index]

            # draw the page while holding the lock, so that it doesn't change
            #  underneath us
            self._curPage.draw_page()
            logging.debug("Transitioned to page %s", self._curPage)

    def showLowBatteryWarning(self):
        if self._curPage == self.low_battery_page:
            # nothing to do
            return

        with self._curPageLock:
            logging.debug("Current page is %s", self._curPage)
            self._curPage = self.low_battery_page
            self._curPage.draw_page()
            logging.debug("Transitioned to page %s", self._curPage)

    def showPoweringOff(self):
        if self._curPage == self.power_down_page:
            # nothing to do
            return

        with self._curPageLock:
            logging.debug("Current page is %s", self._curPage)
            self._curPage = self.power_down_page
            self._curPage.draw_page()
            logging.debug("Transitioned to page %s", self._curPage)

    def hideLowBatteryWarning(self):
        if self._curPage == self.low_battery_page:
            self.powerOffDisplay()

    def powerOffDisplay(self):

        DISPLAY_TIMEOUT_SECS = 120

        if self._curPage == self.blank_page:
            # nothing to do
            return
        if ((self.pageStack == 'wait') or (self.pageStack == 'remove_usb')):
            if self.pageStack == 'wait': self.showWaitPage(a)  # we do not want to reset if we're on a wait screen
            hat.displayPowerOffTime = time.time() + DISPLAY_TIMEOUT_SECS  # reset
            return  # keep waiting
        if self.pageStack != 'status':  # if we're not on the default status pages
            self.pageStack = 'admin'  # this is to prep to return to the status pages
            self.switchPages()  # switch to the status stack from anywhere else we are

        with self._curPageLock:
            logging.debug("Current page is %s", self._curPage)
            self._curPage = self.blank_page
            self._curPage.draw_page()
            logging.debug("Transitioned to page %s", self._curPage)

    # Ideally this should be a page, like the low battery page
    def drawLogo(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/' + logo_image
        print("Logo Image is: " + logo_image)
        logo = Image.open(img_path).convert("RGBA")
        fff = Image.new(logo.mode, logo.size, (255,) * 4)
        background = Image.new("RGBA", self.display_device.size, "black")
        posn = ((self.display_device.width - logo.width) // 2, 0)
        img = Image.composite(logo, fff, logo)
        background.paste(img, posn)
        self.display_device.display(
            background.convert(self.display_device.mode)
        )


    # Function to redraw the current page for use in 
    # refreshing the page during long display times
    def redrawCurrentPage(self):
        with self._curPageLock:
            if (self.pageStack == 'wait'): self.showWaitPage(a)
            else: self._curPage.draw_page()







