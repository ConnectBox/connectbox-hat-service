# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import threading
from distutils.dir_util import copy_tree



class USB:

    def __init__(self):
        pass

    def isUsbPresent(self, devPath = '/dev/sda1'):
        '''
        Returns if there is a USB plugged into specified devPath
        :return: True / False
        '''
        logging.debug("Checking to see if usb is mounted")
        return os.path.exists(devPath)


    def unmount(self, curPath = '/media/usb0'):
        '''
        Unmount the USB drive from curPath
        :return:  True / False
        '''
        try:
            logging.debug("Unmounting file at location {}".format(curPath))
            response = subprocess.call(['umount', curPath])  # unmount drive
            return True if response == 0 else False
        except:
            return False

    def mount(self, devPath = '/dev/sda1', newPath = '/media/usb1'):
        '''
        Mount the USB drive at the devPath to the specified newPath location

        :return: True / False
        '''

        # try:
        logging.debug("Mounting USB at {} to {}".format(devPath, newPath))
        if not os.path.exists(newPath):  # see if desired mounting directory exists
            os.makedirs(newPath)  # if not, make it, and all of the intermediary directories if needed
        response = subprocess.call(['mount','-o', 'sync,noexec,nodev,noatime,nodiratime,utf8', devPath, newPath])
        logging.debug("Response: {}".format(response))
        return True if response == 0 else False
        # except:
        #     return False

    def copyFiles(self, sourcePath = '/media/usb1', destPath = '/media/usb0'):
        '''
        Move files from sourcePath to destPath recursively
        :param sourcePath: place where files are
        :param destPath:  where we want to copy them to
        :return:  True / False
        '''

        if os.path.exists(sourcePath) and os.path.exists(destPath):
            logging.debug("Copying tree")
            try:
                copy_tree(sourcePath, destPath)
                logging.debug("Done copying")
                return True
            except:
                return False
        else:
            return False

    def checkSpace(self, sourcePath = '/media/usb1', destPath = '/media/usb0'):
        '''
        Function to make sure there is space on destination for source materials

        :param sourcePath: path to the source material
        :param destPath:  path to the destination
        :return: True / False
        '''
        if os.path.exists(sourcePath) and os.path.exists(destPath):
            sourceSize = self.getSize(sourcePath)
            destSize = self.getFreeSpace(destPath)
            logging.debug("Source size: {} bytes, destination size: {} bytes".format(sourceSize, destSize))
            # if destSize >= sourceSize :
            if destSize < sourceSize :    # test check
                return True
            else:
                return False
        else:
            return False

    def getSize(self, startPath='/media/usb1'):
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

    def getFreeSpace(self, path='/media/usb0'):
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

    def moveMount(self, devMount = '/dev/sda1', curMount = '/media/usb0', destMount = '/media/usb1'):
        '''
        This is a wrapper for umount, mount.  This is simple and works.
        we could use mount --move  if the mount points are not within a mount point that is marked as shared,
        but we need to consider the implications of non-shared mounts before doing it

        :param devMount: device name in the /dev listing
        :param curMount: where usb is currently mounted
        :param destMount: where we want the usb to be mounted
        :return: True / False
        '''

        self.unmount(curMount)
        return self.mount(devMount, destMount)
