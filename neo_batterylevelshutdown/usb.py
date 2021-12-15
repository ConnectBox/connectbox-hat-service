
import logging
import os
import time
import subprocess
from distutils.dir_util import copy_tree


class USB:

    def __init__(self):
        pass

    @staticmethod
    def isUsbPresent(devPath='/dev/sda1'):
        '''
        Returns if there is a USB plugged into specified devPath
        :return: True / False
        '''
        return os.path.exists(devPath)

    @staticmethod
    def unmount(curPath='/media/usb0'):
        '''
        Unmount the USB drive from curPath
        :return:  True / False
        '''
        logging.debug("Unmounting file at location %s", curPath)
        response = subprocess.call(['umount', curPath])  # unmount drive
        return response == 0

    @staticmethod
    def mount(devPath='/dev/sda1', newPath='/media/usb11'):
        '''
        Mount the USB drive at the devPath to the specified newPath location

        :return: True / False
        '''
        x = ord(devPath[len(devPath)-2])
#   Find the first USB key in the system
        while not os.path.exists(devPath) and (x < ord('k')):
            x = ord(devPath[len(devPath)-2]) + 1
            devPath = "/dev/sd"+chr(x)+"1"

        # try:
        logging.debug("Mounting USB at %s to %s", devPath, newPath)
        if not os.path.exists(newPath):  # see if desired mounting directory exists
            os.makedirs(newPath)  # create directory and all of the intermediary directories
        response = subprocess.call(['mount', '-o', 'sync,noexec,nodev,noatime,nodiratime,utf8',
                                    devPath, newPath])
        logging.debug("Response: %s", response)
        return response == 0

    @staticmethod
    def copyFiles(sourcePath='/media/usb11', destPath='/media/usb0'):
        '''
        Move files from sourcePath to destPath recursively
        To do this we need to turn off automount temporarily by creating a file
        /usr/local/connectbox/PauseMount

        We must delete this if we exit at any point

        :param sourcePath: place where files are if it is '/media/usb0' then thats all that is copied, if it
        :  something other than /media/usb0 it will looop through the usb's excluding 0 to copy to the dest (/media/usb0)
        :param destPath:  where we want to copy them to
        :return:  True / False
        '''
        logging.info("Copying from: "+sourcePath+" to: "+destPath)
        with open('/usr/local/connectbox/PauseMount', "w") as fp:
            pass
        fp.close()
        time.sleep(2)  # give time for Pause of the Mount
        y = 0
        if sourcePath != '/media/usb11':
            x = ord(sourcePath[len(sourcePath)-1])
            while (not os.path.exists('/media/usb'+chr(x))) and x < ord(':'):
                x +=1
        else: x = ord('0')
        if os.path.exists(destPath):
            while os.path.exists(sourcePath) and (x < ord(':')):
                if os.path.exists(sourcePath) and os.path.exists(destPath):
                    logging.info("Copying tree: "+sourcePath+" to: "+destPath)
                    copy_tree(sourcePath, destPath)
                    y = 1
                    logging.debug("Done copying to: "+destPath)
#   Find the next USB key in the system to copy to destination
                if sourcePath != '/media/usb0':
                    if len(sourcePath)==12: sourcePath = "/media/usb0"
                    x = ord(sourcePath[len(sourcePath)-1]) + 1
                    sourcePath = '/media/usb'+chr(x)
                    while not os.path.exists(sourcePath) and (x < ord(':')):
                        x = ord(sourcePath[len(sourcePath)-1]) + 1
                        sourcePath = "/media/usb"+chr(x)

            if (y == 1):
                logging.info("Everything copied all done")
                return True
            else:
                logging.info("nothing copied alll done")
                return False
        else:
            logging.info("failed destination path")
            return False

    def checkSpace(self, sourcePath='/media/usb11', destPath='/media/usb0'):
        '''
        Function to make sure there is space on destination for source materials

        :param sourcePath: path to the source material
        :param destPath:  path to the destination
        :return: True / False
        '''
        logging.info("Starting the Space Check")
        destSize = self.getFreeSpace(destPath)
        sourceSize = 0
        while os.path.exists(sourcePath):
            sourceSize += self.getSize(sourcePath)
            logging.info("got source size as : "+str(sourceSize)+" Path is: "+sourcePath)
            if sourcePath != "/media/usb0":
                if len(sourcePath) == 12:
                   sourcePath = '/media/usb0'
                x = ord(sourcePath[len(sourcePath) - 1])+1
                sourcePath = '/media/usb'+chr(x)
                while not os.path.exists(sourcePath) and (x< ord(':')):
                   x = ord(sourcePath[len(sourcePath)-1]) + 1
                   sourcePath = "/dev/usb"+chr(x) 
                logging.info("Source size:"+str(sourceSize)+"  bytes, destination size:"+str(destSize)+" Now looking at:"+sourcePath)
            else:
                logging.info("total source size:"+str(sourceSize)+"  bytes, total destination size "+str(destSize))
                return(destSize, sourceSize)
        logging.info("total source size:"+str(sourceSize)+"  bytes, total destination size "+str(destSize))
        return (destSize, sourceSize)

    # pylint: disable=unused-variable
    # Looks like this isn't summing subdirectories?
    @staticmethod
    def getSize(startPath='/media/usb11'):
        '''
        Recursively get the size of a folder structure

        :param startPath: which folder structure
        :return: size in bytes of the folder structure
        '''
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(startPath):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    @staticmethod
    def getFreeSpace(path='/media/usb0'):
        '''
        Determines how much free space in available for copying

        :param path: a path to put us in the right partition
        :return:  size in bytes of free space
        '''

        # this is the cushion of space we want to leave free on our internal card
        freeSpaceCushion = 1073741824  # 1 GiB
        stat = os.statvfs(path)
        free = stat.f_bfree * stat.f_bsize
        adjustedFree = free - freeSpaceCushion
        return adjustedFree

    def moveMount(self, devMount='/dev/sda1', curMount='/media/usb0', destMount='/media/usb11'):
        '''
        This is a wrapper for umount, mount.  This is simple and works.
        we could use mount --move  if the mount points are not within a mount point that is
        marked as shared, but we need to consider the implications of non-shared mounts before
        doing it

        Find the first USB key by device
        '''
        x = ord(devMount[len(devMount)-2])
        while not os.path.exists(devMount) and (x < ord('k')):
            x = ord(devMount[len(devMount)-2]) + 1
            devMount = "/dev/sd"+chr(x)+"1"

# take the file mount outuput and separate it into lines
        mounts = str(subprocess.check_output(['df']))
        mounts = mounts.split("\\n")

# take the lines and check for the mount.
        for line in mounts:
            if (devMount in line) and (curMount in line):
                x = True
                break
            else:
                x = False

        '''
        #:param devMount: device name in the /dev listing
        #:param curMount: where usb is currently mounted
        #:param destMount: where we want the usb to be mounted
        #:return: True / False
        '''

        if x:
            with open('/usr/local/connectbox/PauseMount', "w") as fp:
                pass
            fp.close()
            time.sleep(2)  # give time for Pause of the Mount
            self.unmount(curMount)
            return self.mount(devMount, destMount)
        else:
            return x


    def getDev(self, curMount):
        '''
        This is a method of getting the device for the mount point
        '''
# take the file mount outuput and separate it into lines
        mounts = str(subprocess.check_output(['df']))
        mounts = mounts.split("\\n")

# take the lines and check for the mount.
        for line in mounts:
            if (curMount in line):
                x = line.split(" ", 1)
                x = x[0].rstrip(" ")
                x = ''.join(x)
                break
            else:
                x = ""
        return x



    def getMount(self, curDev):
        '''
        This is a method of getting the device for the mount point
        '''
# take the file mount outuput and separate it into lines
        mounts = str(subprocess.check_output(['df']))
        mounts = mounts.split("\\n")

# take the lines and check for the mount.
        for line in mounts:
            if (curDev in line):
                x = line.split("%", 1)
                x = x[1].rstrip(" ")
                x = x.lstrip(" ")
                x = ''.join(x)
                break
            else:
                x = ""
        return x



