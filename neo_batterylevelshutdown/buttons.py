#! /usr/bin/python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import shutil
import os
from . import page_display_image
import time
import threading
import neo_batterylevelshutdown.usb as usb
import neo_batterylevelshutdown.hats as hat
import json
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


comsFileName = "/tmp/creating_menus.txt"
DEBUG = True

class BUTTONS:
    """Handles physical button input for ConnectBox HATs.

    Translates raw GPIO edge interrupts into display navigation commands.
    Two buttons are supported: left (index 0 of USABLE_BUTTONS) and right
    (index 1).  Press semantics:

      Short single press  — left: move forward through status pages;
                            right: enter/confirm in admin stack.
      Short dual press    — both buttons simultaneously for < threshold seconds:
                            treated as a single short press on the first button.
      Long press          — single button held >= CHECK_PRESS_THRESHOLD_SEC:
                            initiates device shutdown.
      Long dual press     — both buttons held >= CHECK_PRESS_THRESHOLD_SEC:
                            switchPages() (toggles status ↔ admin stack).

    BUTTON_PRESS_BUSY and BUTTON_PRESS_CLEARED_TIME together implement a
    software debounce and re-entrancy guard so rapid or simultaneous presses
    only produce one response.
    """

    BUTTON_PRESS_BUSY = False  # Prevent dual usage of the handleButtonPress function
    BUTTON_PRESS_TIMEOUT_SEC = 0.25  # Prevent bouncing of the handleButtonPress function
    BUTTON_PRESS_CLEARED_TIME = time.time()  # When was the handleButtonPress was last cleared
    CHECK_PRESS_THRESHOLD_SEC = 4  # Threshold for what qualifies as a long press and limit to the length of time in the interrupt routine
    DISPLAY_TIMEOUT_SECS = 120     #screen on time before auto off

    def __init__(self, hat_class, display_class):
        """Bind the BUTTONS instance to its HAT and display objects.

        Parameters
        ----------
        hat_class     : Axp209HAT subclass instance
        display_class : OLED instance — used to push pages to the screen
        """
        self.display = display_class
        self.hat = hat_class
        self.display_type = display_class.display_type
        self.USABLE_BUTTONS = self.hat.USABLE_BUTTONS
        self.command_to_reference = ''
        self.l = []
        # True while an admin command (copy / erase) runs: the HAT main loop then
        # leaves the screen to the command and does not blank it
        self.admin_busy = False

    def checkReturn(self, val):
        """Write val to usb0NoMount in brand.j2, then sleep 4 s so PxUSBm can catch up.

        Used by USB copy/erase commands to temporarily disable auto-mount while
        files are being copied.  Returns the original usb0NoMount value so the
        caller can restore it when the operation completes.

        Parameters
        ----------
        val : str or int — new value to write to usb0NoMount ('0' or '1')

        Returns
        -------
        original usb0NoMount value read from brand.j2 before the write.
        """
        brand = globals.read_brand()
        NoMountOrig = (brand['usb0NoMount'])
        brand['usb0NoMount'] = val
        globals.write_brand(brand)      # whole file, renamed into place
        time.sleep(4)       #sleep to allow PxUSBm to catch up
        return(NoMountOrig)


    # ── Admin commands (copy from / to USB, erase) ─────────────────────────────
    #
    # The box's own content lives in /media/usb0/content when no USB key is
    # mounted there.  Each command stops PxUSBm from mounting keys at
    # /media/usb0 (usb0NoMount = 1) while it works, mounts the key at
    # /media/usb11 instead, checks the space BEFORE deleting anything, and
    # always puts usb0NoMount back.  Every failure leaves an error page on the
    # screen (pageStack 'error'; either button returns to the admin menu), and
    # the screen is never left showing "success" for something that did not
    # happen.  While a command runs, admin_busy tells the HAT main loop not to
    # draw its own pages or blank the display.

    ADMIN_MOUNT = '/media/usb11'       # where the key is mounted while copying
    INTERNAL = '/media/usb0'           # the box's own content folder (when no key is mounted there)
    CONTENT = '/content/'
    USB_WAIT_SECS = 300                # how long to wait for a key to be inserted / removed

    def _keepDisplayOn(self):
        self.hat.displayPowerOffTime = sys.maxsize

    def _resetDisplayTimer(self):
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def _wait(self, text):
        """Show the animated wait page with text (the main loop keeps it animated)."""
        globals.a = text
        globals.sequence = 0
        self.display.pageStack = 'wait'
        self.display.showWaitPage(text)

    def _error(self, text):
        """Show an error page that stays until a button is pressed; returns False."""
        logging.info("Admin command failed: %s", text)
        print("Admin command failed: " + text)
        self.display.pageStack = 'error'
        self.display.showErrorPage(text)
        self._resetDisplayTimer()
        return False

    def _success(self):
        self.display.pageStack = 'success'
        self.display.showSuccessPage()
        self._resetDisplayTimer()
        return True

    def _setNoMount(self, val):
        """Set usb0NoMount in brand.j2; return the previous value (None if it could not be read)."""
        try:
            return self.checkReturn(val)
        except Exception as e:     # missing or damaged brand.j2
            logging.error("Could not set usb0NoMount: %s", e)
            return None

    def _restoreNoMount(self, orig):
        if orig is not None:
            try:
                self.checkReturn(orig)
            except Exception as e:
                logging.error("Could not restore usb0NoMount: %s", e)

    def _waitForUsb(self):
        """Return the first USB key's device (/dev/sdX1), asking for one if none is in.  "" if none came."""
        dev = usb.isUsbPresent()
        if dev != "":
            return dev
        self.display.pageStack = 'insertUSB'
        self.display.showInsertUsbPage()
        end = time.time() + self.USB_WAIT_SECS
        while time.time() < end:
            time.sleep(2)
            dev = usb.isUsbPresent()
            if dev != "":
                time.sleep(3)       # let the key settle before mounting it
                return dev
        return ""

    def _waitForRemoval(self, dev):
        """Show the remove-USB page until the key is pulled out (or USB_WAIT_SECS pass)."""
        self.display.pageStack = 'remove_usb'
        self.display.showRemoveUsbPage()
        end = time.time() + self.USB_WAIT_SECS
        while usb.isUsbPresent(dev) == dev and time.time() < end:
            time.sleep(2)

    def _service(self, command):
        """Run a systemctl command; returns its exit status (0 = ok)."""
        return os.system("systemctl " + command + " >/dev/null 2>&1")

    def _releaseKey(self):
        """
        Stop what keeps files open on the key mounted at /media/usb0 so it can
        be unmounted: content indexing (connectbox-loader) and kiwix-serve,
        which holds the key's .zim files open.  PxUSBm does the same when a
        key is removed.  kiwix-serve is started again by _restoreServices().
        """
        self._service("stop connectbox-loader.service")
        if self._service("is-active --quiet kiwix-serve.service") == 0:
            self._service("stop kiwix-serve.service")
            self._kiwixStopped = True

    def _restoreServices(self):
        """
        Make sure kiwix-serve runs after an admin command: started again if
        _releaseKey() stopped it, and also if an earlier command stopped it
        and the service was restarted before it could (seen on a test box:
        a crash left kiwix-serve stopped and the next copy did not start it).
        Only if it is enabled at boot, i.e. Kiwix is set up on this box.
        """
        self._kiwixStopped = False
        if self._service("is-enabled --quiet kiwix-serve.service") == 0 and \
                self._service("is-active --quiet kiwix-serve.service") != 0:
            self._service("start kiwix-serve.service")

    def _mountKey(self, dev):
        """
        Mount the key at ADMIN_MOUNT (moving it off /media/usb0 if PxUSBm
        mounted it there).  Returns the mount point, or "" on failure.
        """
        mnt = usb.getMount(dev)
        if mnt not in ("", self.INTERNAL):
            return mnt                                  # already mounted somewhere else: use it
        if not os.path.exists(self.ADMIN_MOUNT):
            os.mkdir(self.ADMIN_MOUNT)
        if mnt == self.INTERNAL:
            self.movedFromUsb0 = True       # PxUSBm will clean up after it once it is removed
            self._releaseKey()
            ok = False
            for attempt in range(3):            # a file being downloaded can hold it briefly
                ok = usb.moveMount(self.INTERNAL, self.ADMIN_MOUNT) == 0
                if ok or usb.getMount(dev) != self.INTERNAL:
                    break
                time.sleep(3)
            if not ok and usb.getMount(dev) == self.INTERNAL:
                self.busyKey = True             # still mounted at /media/usb0: something has files open
        else:
            ok = bool(usb.mount(dev, self.ADMIN_MOUNT))
        if not ok or usb.getDev(self.ADMIN_MOUNT) == "":
            return ""
        return self.ADMIN_MOUNT

    def _startContentLoader(self):
        """Re-index the box's content the same way PxUSBm does (start_content_loader)."""
        os.system("systemctl stop connectbox-loader.service 2>/dev/null; "
                  "systemctl reset-failed connectbox-loader.service 2>/dev/null")
        for _ in range(10):         # give systemd up to 5 s to unload the old unit
            state = subprocess.run(['systemctl', 'show', '-p', 'LoadState', '--value', 'connectbox-loader.service'],
                                   stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
            if state != 'loaded':
                break
            time.sleep(0.5)
        os.system("/usr/bin/systemd-run --unit=connectbox-loader --description='ConnectBox Content Loader' "
                  "--remain-after-exit /usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py")

    USB0_INDEXED = '/tmp/.usb0_indexed'    # PxUSBm's "usb0 was indexed" sentinel
    PXUSBM_CLEANUP_SECS = 30

    def _restoreAndReindex(self, orig):
        """
        Put usb0NoMount back, then re-index the box's content.  When mount
        checks resume, PxUSBm notices that the key it had at /media/usb0 is
        gone and does its removal clean-up: it stops connectbox-loader, empties
        the Kiwix library and the menus (mmiLoader --clear), then deletes
        /tmp/.usb0_indexed.  Starting the re-index before that finished would
        have it stopped and the new menus wiped, so wait for the sentinel to
        go first (only when PxUSBm will run mount checks).
        """
        self._restoreNoMount(orig)
        try:
            pxusbm_active = int(orig) <= 0
        except (TypeError, ValueError):
            pxusbm_active = False
        if pxusbm_active:
            end = time.time() + self.PXUSBM_CLEANUP_SECS
            while os.path.exists(self.USB0_INDEXED) and time.time() < end:
                time.sleep(1)
            if self._hasContent(self.INTERNAL + self.CONTENT):
                # PxUSBm indexes the box's own content whenever no key is at
                # /media/usb0 (check_internal_content), once per marker.
                # Clear the marker and let it, so the loader starts once
                # (both starting it stopped the first run).  If it has not
                # started within PXUSBM_INDEX_SECS (an older PxUSBm), start it.
                started = time.monotonic()
                try:
                    os.remove(self.INTERNAL_INDEXED)
                except OSError:
                    pass
                end = time.time() + self.PXUSBM_INDEX_SECS
                while True:
                    if self._loaderStartedSince(started):
                        return
                    if time.time() >= end:
                        break
                    time.sleep(max(0.1, min(1, end - time.time())))
                logging.warning("PxUSBm did not start the content loader; starting it")
        self._startContentLoader()

    INTERNAL_INDEXED = '/tmp/.internal_indexed'   # PxUSBm: box's own content indexed
    PXUSBM_INDEX_SECS = 30

    @staticmethod
    def _hasContent(path):
        try:
            return any(not name.startswith('.') for name in os.listdir(path))
        except OSError:
            return False

    @staticmethod
    def _loaderStartedSince(t0):
        """True if connectbox-loader was started after time.monotonic() t0."""
        try:
            out = subprocess.run(['systemctl', 'show', '-p', 'ExecMainStartTimestampMonotonic', '--value',
                                  'connectbox-loader.service'], stdout=subprocess.PIPE,
                                 universal_newlines=True, timeout=10).stdout.strip()
            return int(out or 0) / 1e6 > t0
        except (OSError, ValueError, subprocess.SubprocessError):
            return False

    def _indexingHandover(self):
        """
        After a command that re-indexes: show a wait page now and let the HAT
        main loop show the loader's progress and ONE success page when the
        menus are ready (before, the command showed success and the main loop
        showed a second one).  pageStack 'success': a press goes back to the
        admin menu as after any success page (never re-runs the command).
        """
        self._wait("Indexing")
        self.display.pageStack = 'success'
        self._resetDisplayTimer()

    COPY_PROGRESS_SECS = 3         # how often the copy's percentage is updated

    @staticmethod
    def _copyText(percent, needed):
        """Wait page text during a copy, e.g. "Copying 45%\nSize:22431MB"."""
        return "Copying %d%%\nSize:%dMB" % (percent, int(needed / 1000000))

    @staticmethod
    def _freeBytes(path):
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize

    def _copyWithProgress(self, src, dest, needed):
        """
        usb.copyFiles(src, dest) with the percentage done on the wait page.
        shutil.copytree reports nothing while it runs, so a watcher thread
        measures how much free space the destination has lost since the copy
        started (this also moves during one very large file, e.g. a ZIM) and
        puts it in globals.a, which the HAT main loop redraws.  Never shows
        100% before the copy has returned.  Returns copyFiles' result.
        """
        stop = threading.Event()
        try:
            free0 = self._freeBytes(dest)
        except OSError:
            free0 = None

        def watch():
            while not stop.wait(self.COPY_PROGRESS_SECS):
                if free0 is None or not needed:
                    continue
                try:
                    done = free0 - self._freeBytes(dest)
                except OSError:
                    continue
                globals.a = self._copyText(max(0, min(99, int(100 * done / needed))), needed)

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            return usb.copyFiles(src, dest, self.CONTENT)
        finally:
            stop.set()
            watcher.join(5)

    @staticmethod
    def _folderSize(path):
        return usb.getSize(path) if os.path.isdir(path) else 0

    def _removeFolder(self, path):
        if os.path.isdir(path):
            shutil.rmtree(path)

    def copyFromUsb(self):
        """Replace the box's content with the USB key's /content/ folder."""
        orig = self._setNoMount(1)
        dev = ""
        try:
            dev = self._waitForUsb()
            if dev == "":
                return self._error("No USB key")
            self._wait("Checking USB")
            mnt = self._mountKey(dev)
            if mnt == "":
                return self._error("USB busy" if self.busyKey else "USB not mounted")
            if usb.getDev(self.INTERNAL) != "":
                return self._error("Remove 2nd USB")       # another key sits where the content goes
            if not os.path.isdir(mnt + self.CONTENT):
                return self._error("No content dir")
            self._wait("Checking Space")
            os.makedirs(self.INTERNAL, exist_ok=True)
            (free, needed) = usb.checkSpace(mnt, self.INTERNAL)
            if needed == 0:
                return self._error("Nothing to copy")
            if free + self._folderSize(self.INTERNAL + self.CONTENT) < needed:
                return self._error("Not enough room")
            self._wait(self._copyText(0, needed))
            self._removeFolder(self.INTERNAL + self.CONTENT)
            if self._copyWithProgress(mnt, self.INTERNAL, needed) > 0:
                return self._error("Failed Copy")
            os.sync()
            usb.unmount(mnt)
            self._waitForRemoval(dev)
            self._indexingHandover()
            self._restoreAndReindex(orig)
            orig = None                 # already put back
            self.hat.indexPending = True
            return True
        finally:
            if dev != "" and usb.getMount(dev) == self.ADMIN_MOUNT:
                os.sync()
                usb.unmount(self.ADMIN_MOUNT)
            self._restoreNoMount(orig)

    def copyToUsb(self):
        """Copy the box's /content/ folder onto a USB key (replacing the key's /content/)."""
        orig = self._setNoMount(1)      # keep PxUSBm from mounting (and indexing) the key at /media/usb0
        dev = ""
        try:
            dev = self._waitForUsb()
            if dev == "":
                return self._error("No USB key")
            self._wait("Checking USB")
            mnt = self._mountKey(dev)
            if mnt == "":
                return self._error("USB busy" if self.busyKey else "USB not mounted")
            if usb.getDev(self.INTERNAL) != "":
                return self._error("Remove 2nd USB")       # content would come from that key, not the box
            self._wait("Checking Space")
            (free, needed) = usb.checkSpace(self.INTERNAL, mnt)
            if needed == 0:
                return self._error("Nothing to copy")
            if free + self._folderSize(mnt + self.CONTENT) < needed:
                return self._error("Not enough room")
            self._wait(self._copyText(0, needed))
            try:
                self._removeFolder(mnt + self.CONTENT)
            except OSError as e:
                logging.error("Could not clear %s: %s", mnt + self.CONTENT, e)
                return self._error("Failed deletion")
            if self._copyWithProgress(self.INTERNAL, mnt, needed) > 0:
                return self._error("Failed Copy")
            os.sync()
            usb.unmount(mnt)
            self._waitForRemoval(dev)
            if self.movedFromUsb0:
                # The box was serving this key: it now serves its own content again
                self._indexingHandover()
                self._restoreAndReindex(orig)
                orig = None
                self.hat.indexPending = True
            else:
                self._success()
            return True
        finally:
            if dev != "" and usb.getMount(dev) == self.ADMIN_MOUNT:
                os.sync()
                usb.unmount(self.ADMIN_MOUNT)
            self._restoreNoMount(orig)

    def eraseFolder(self):
        """Delete the box's own content (/media/usb0/content); a USB key must be removed first."""
        orig = self._setNoMount(1)      # keep PxUSBm from mounting the key again while we wait for it
        try:
            return self._eraseFolder(orig)
        finally:
            if self._eraseOrig is not None:
                self._restoreNoMount(self._eraseOrig)

    def _eraseFolder(self, orig):
        self._eraseOrig = orig
        dev = usb.isUsbPresent()
        if dev != "":
            mnt = usb.getMount(dev)
            if mnt != "":
                if mnt == self.INTERNAL:
                    self._releaseKey()
                os.sync()
                usb.unmount(mnt)
            self._waitForRemoval(dev)
            if usb.isUsbPresent(dev) == dev:
                return self._error("USB not removed")
        if usb.getDev(self.INTERNAL) != "":
            return self._error("USB in use")        # never erase a key by mistake
        self._wait("Erasing")
        folder = self.INTERNAL + self.CONTENT
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
        logging.debug("Content folder erased")
        self._indexingHandover()
        self._eraseOrig = None
        self._restoreAndReindex(orig)
        self.hat.indexPending = True
        return True

    def removeUsb(self):
        """Ask for the USB key to be removed and wait until it is."""
        dev = usb.isUsbPresent()
        if dev != "":
            os.sync()
            self._waitForRemoval(dev)
        return self._success()

    def executeCommands(self, command):
        '''
        Run the admin command chosen on the display.  Returns True on success,
        False on failure (an error page is then on the screen).
        '''
        if not (self.hat.batteryLevelAboveVoltage(self.hat.BATTERY_WARNING_VOLTAGE)):
            # Not enough battery to finish a copy safely
            return self._error("Battery low")
        commands = {
            'remove_usb': self.removeUsb,
            'copy_from_usb': self.copyFromUsb,
            'copy_to_usb': self.copyToUsb,
            'erase_folder': self.eraseFolder,
        }
        if command not in commands:
            return self._error("Unknown choice")
        print("Execute Command: " + command)
        self.admin_busy = True
        self.busyKey = False
        self.movedFromUsb0 = False
        self._keepDisplayOn()
        try:
            return commands[command]()
        except Exception as e:
            logging.exception("Admin command %s failed", command)
            return self._error("Error - see log")
        finally:
            self._restoreServices()
            self.admin_busy = False
            self._resetDisplayTimer()

###########################################################################################################
# Button Presses go here from the interrupt handler
##########################################################################################################


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

        print("we had a button press")
        if self.display_type == 'DummyDisplay':                                           # this device has no buttons or display, skip
            return

        # this section is to prevent both buttons calling this method and getting two replies
        if self.BUTTON_PRESS_BUSY:  # if flag is set that means this method is currently being used
            print("skipping button press - BUSY flag")
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

        logging.debug("time stamp for channel Time line 524: %s", channelTime)
        logging.debug("time stamp for dualTime line 525: %s", dualTime)

        # clear the CHECK_PRESS_BUSY flag
        self.BUTTON_PRESS_BUSY = False

        # reset the CHECK_PRESS_CLEARED_TIME to now
        self.BUTTON_PRESS_CLEARED_TIME = time.time()

        pageStack = self.display.pageStack  # shortcut
        print ("PAGESTACK: %s", pageStack)
        if pageStack == 'wait':
            # A command is running: a press here used to reach chooseEnter,
            # which runs the last command (e.g. the copy) again
            return
        print ("COMMAND: %s", self.command_to_reference)

        # this is where we decide what to do with the button press.  ChanelTime is the first
        # button pushed, dualTime is the amount of time both buttons were pushed.
        if channelTime < .1:  # Ignore noise
            pass

        # if either button is below the press threshold, treat as normal
        elif channelTime < (self.CHECK_PRESS_THRESHOLD_SEC ) or \
                dualTime < (self.CHECK_PRESS_THRESHOLD_SEC ):
            print("hit self.check_press_threshold_sec line 655")
            if channel == self.USABLE_BUTTONS[0]:                                           # this is the left button
                print("Left button: pageStack ="+str(pageStack))
                if pageStack in ['success']:                # return to 1st page of admin stack
                    self.moveToStartPage(channel)
                elif pageStack in ['confirm', 'error', 'error_no_space', 'error_no_space2']:     # return to first page admin stack
                    self.display.pageStack = 'admin'
                    self.chooseCancel(pageStack)
                elif pageStack in ['remove_usb']:            # never reach here... loops elsewhere until they remove the USB stick
                    self.chooseEnter(pageStack)
                else:                                       # anything else, we treat as a moveForward (default) function
                    self.moveForward(channel)
            else:                                                                           # right button
                print("Right button: pageStack ="+str(pageStack))
                if pageStack in ['success']:                # return to 1st page of admin stack
                    self.moveToStartPage(channel)
                elif pageStack == 'status':                 # standard behavior - status stack
                    self.moveBackward(channel)
                elif pageStack in ['error']:                # both conditions return to admin stack
                    self.chooseCancel(pageStack)
                else:                                       # this is an enter key in the admin stack
                    self.chooseEnter(pageStack)

        # if we have a long press (both are equal or greater than threshold) call switch pages
        elif channelTime >= self.CHECK_PRESS_THRESHOLD_SEC or \
                dualTime >= self.CHECK_PRESS_THRESHOLD_SEC :
            print("hats 576 hit dual button press time, move forward admin")
            print("hats 576 hit dual button press time, move forward admin",channelTime,dualTime)
            self.switchPages()


    def checkPressTime(self, channel):
        '''
        Time a button press.  Returns (how long the pressed button was held,
        longest time both buttons were held together).

        - Both buttons held together for CHECK_PRESS_THRESHOLD_SEC returns at
          once (the caller switches between the status and admin pages).  The
          time counts from when the second button went down, so the two need
          not be pressed at the same instant.
        - One button held on its own for CHECK_PRESS_THRESHOLD_SEC shuts the
          box down.  If the other button was pressed at any moment during the
          press it is never a shutdown (someone reaching for the admin menu).

        USABLE_BUTTONS holds the two pins (left first); the one not passed in
        as channel is the other button.
        '''
        otherChannel = self.USABLE_BUTTONS[0] if channel == self.USABLE_BUTTONS[1] else \
            self.USABLE_BUTTONS[1]
        threshold = self.CHECK_PRESS_THRESHOLD_SEC

        # NEO ONLY: turn off the push button interrupts (PG6 / PG7) while we
        #  read the pins as plain inputs; they are turned back on below.
        if (globals.device_type == "NEO"):
            os.popen("devmem2 0x01c208d8 w 0x00777777 >/dev/null").read()

        startTime = time.time()
        dualStartTime = None        # when both buttons were last seen going down together
        dualTimeRecorded = 0.0      # longest time both were down (kept so release bounce cannot shorten it)
        otherSeen = False
        try:
            while GPIO.input(channel) == 0:
                now = time.time()
                if GPIO.input(otherChannel) == 0:
                    otherSeen = True
                    if dualStartTime is None:
                        dualStartTime = now
                    dualTimeRecorded = max(dualTimeRecorded, now - dualStartTime)
                    if dualTimeRecorded >= threshold:
                        break                                   # long dual press
                else:
                    dualStartTime = None
                if not otherSeen and now - startTime >= threshold:
                    break                                       # long single press
                if now - startTime > threshold * 3:
                    break                                       # never stay in here for ever
                time.sleep(0.01)
        finally:
            # We are through reading the buttons, so turn interrupt handling back on
            if (globals.device_type == "NEO"):
                os.popen("devmem2 0x01c208d8 w 0x66777777 >/dev/null").read()

        buttonTime = time.time() - startTime
        print("    buttonTime = " + str(buttonTime) + " dualTimeRecorded = " + str(dualTimeRecorded))
        if dualTimeRecorded >= threshold or otherSeen or buttonTime < threshold:
            return buttonTime, dualTimeRecorded

        # A single button held on its own: shut down
        print("single long button press - shutting down", buttonTime)
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS
        self.hat.shutdownDevice()
        return buttonTime, dualTimeRecorded


    def chooseCancel(self, pageStack):
        """Cancel a choice (or leave an error page): back to the admin item that was chosen."""
        logging.debug("Choice cancelled")
        if hasattr(self.display, 'showAdminPage'):         # displays.py from connectbox-pi
            self.display.showAdminPage(self.command_to_reference)
        else:                                               # older displays.py: first admin item
            self.display.pageStack = 'admin'
            self.display.moveForward()
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
            print("choice confirmed command to reference: ",self.command_to_reference)
            globals.sequence = 0
#            self.display.showWaitPage()
#            self.display.pageStack = 'wait'
#            logging.debug("Waiting Page shown")
            self.executeCommands(self.command_to_reference)

        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def switchPages(self):
        """method for use on button press to change display options"""
        logging.debug("You have now entered, the SwitchPages")
        self.display.switchPages()
        # reset the display power off time
        self.hat.displayPowerOffTime = time.time() + self.DISPLAY_TIMEOUT_SECS

    def moveToStartPage(self, channel):
        """Jump to the first page of the current page stack and reset the display timeout.

        Parameters
        ----------
        channel : int — GPIO pin that triggered the press (passed through but not used here)
        """
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
