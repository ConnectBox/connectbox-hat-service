import logging
import os
import time
import subprocess
import shutil


class USB:

    def __init__(self):
        pass

    @staticmethod
    def isUsbPresent(devPath='/dev/sda1'):
        '''

        Returns if there is a USB plugged into specified devPath
        (does not depend on stick being mounted)
        :return: True / False
        '''
        return(os.path.exists(devPath))

    @staticmethod
    def unmount(curPath='/media/usb0'):
        '''
        Unmount the USB drive from curPath
        :return:  True / False
        '''
        logging.debug("Unmounting file at location %s", curPath)
        response = subprocess.call(['umount', curPath])  # unmount drive
        return(response)

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

        logging.debug("Mounting USB at %s to %s", devPath, newPath)
        if not os.path.exists(newPath):  # see if desired mounting directory exists
            os.makedirs(newPath)  # create directory and all of the intermediary directories
        response = subprocess.call(['mount', '-o', 'sync,noexec,nodev,noatime,nodiratime,utf8',
                                    devPath, newPath])
        logging.debug("Response: %s", response)
        return(response)

    @staticmethod
    def copyFiles(sourcePath='/media/usb11', destPath='/media/usb0', ext='/content/'):
        '''
        Move files from sourcePath to destPath recursively
        To do this we need to turn off automount temporarily by changing the usb0NoMount flag in brand.txtg

        :param sourcePath: place where files are if it is '/media/usbX' it will copy the files from that mount and then it will loop through the
        remaining usb's excluding to copy to the dest (/media/usb0)
        :param destPath:  where we want to copy them to
        :return:  True / False
        '''
        logging.info("Copying from: "+sourcePath+" to: "+destPath)
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
        y = 0
        a = sourcePath
        b = ext

        if (not os.path.exists(a+b)):
            c = getMount(a)
            if x != "":
                if (ord(c[-2]+ord(c[-1])).isnumeric()):
                    x = ";"
                else:
                    x = ord(c[-1])
            while ((not os.path.exists('/media/usb'+chr(x)+b)) and (x < ord(':')) and (x != "")):
                x +=1
            logging.info("didn't have right usb mount so looked for one and got /media/usb"+chr(x)+b)
        if (os.path.isdir(destPath) and (x != ord(":")) and (x != "")):
#                if os.path.isdir(destPath+b):
#                    shutil.rmtree((destPath+b), ignore_errors=True)             #erase all data in source directory
            errors=[]
            while (os.path.exists(a+b) and (x <= ord(';') and (x != ord(':')))):
                if os.path.exists(a+b) and os.path.exists(destPath):
                    files_in_dir = str(a+b)
                    files_to_dir = str(destPath+b)
                    if files_to_dir[-1] != "/": files_t0_dir = files_to_dir + "/"
                    try:
                        if os.path.isdir(files_in_dir):
                            logging.info("Copying tree: "+files_in_dir+" to: "+files_to_dir)
                            shutil.copytree(files_in_dir, files_to_dir, symlinks=False, ignore_dangling_symlinks=True)
                            logging.info("Used copytree to move files")
                        else:
                            logging.info("Copying: "+files_in_dir+" to: "+files_to_dir)
                            shutil.copy2(files_in_dir, files_to_dir)
                            logging.info("used copy2 to move files")
                    except OSError as err:
                        errors.append(files_in_dir, files_to_dir, str(err))
                        y = 1
                    except BaseException as err:
                        errors.extend(files_in_dir, files_to_dir, str(err.args[0]))
                        y = 1
                    try:
                        shutil.copystat(files_in_dir, files_to_dir)
                    except OSError as err:
                        if err.winerror is None:
                        errors.extend(files_in_dir, files_to_dir, str(err))
                            y = 1
                    if y != 1:
                        logging.info("Done copying to: "+a+" to: "+destPath+b)
                    else:
                        logging.info("Done copying "+a+" to: "+destPath+b+" but errored: "+str(errors))
#   Find the next USB key in the system to copy to destination
                else:
                    logging.info("We found the destination of the copy but there is no "+b+" directory or source indicie is out of range")
                    y = 1
                if (not sourcePath in a):
                    if len(a)>=12:
                        if sourcePath == "/media/usb11":
                            a = "/media/usb11"
                        else:
                            a = "/media/usb0"
                    x = ord(a[-1]) + 1
                    a = '/media/usb'+chr(x)
                    while (not os.path.exists(a+b) and (x < ord(':')) or (a in sourcepath):
                        x = ord(a[-1]) + 1
                        a = "/media/usb"+chr(x)
 
            if (y == 0):
                logging.info("Everything copied all done")
                return(0)
            else:
                logging.info("we failed on our copy function")
                return(1)
        else: 
            y = 1
            logging.info("Error on the call of copy due to destination not being a directory or source indicie out of range ")
            if NoMountOrig = 0:
                open('/usr/local/connectbox/brand.txt', "a") as fp:
                m = fp.read()
                if 'usb0NoMount":1' in m:
                    x = str(m).find("usb0NoMount")
                    if x >= 0:
                        m[x+13:x+13] = "0"
                        fp.write(m)
                    fp.close()
                    os.sync()
            return(1)



    def checkSpace(self, sourcePath='/media/usb11', destPath='/media/usb0', sourdest=1):
        '''
        Function to make sure there is space on destination for source materials

        :param sourcePath: path to the source material
        :param destPath:  path to the destination
        :param sourdest : indicates that we are copying source to destination if 1 otherwise were copying destination to source
        :return: True / False
        '''
        logging.info("Starting the Space Check "+sourcePath+" "+destPath)
        destSize = self.getFreeSpace(destPath)
        sourceSize = 0
        y = 0
        a = sourcePath
        b = "/content/"
        while os.path.exists(a+b):
            sourceSize += self.getSize(a+b)
            logging.info("got source size as : "+str(sourceSize)+" Path is: "+a+b)
            if (len(a) < 12):
                x = ord(a[len(a) - 1])+1
                a = '/media/usb'+chr(x)
                while ((not os.path.exists(a)) and (x< ord(':'))):
                   x = ord(a[len(a)-1]) + 1
                   a = "/dev/usb"+chr(x) 
                logging.info("Source size:"+str(sourceSize)+"  bytes, destination size:"+str(destSize)+" Now looking at:"+a+b)
            else:
                logging.info("total source size:"+str(sourceSize)+"  bytes, total destination size "+str(destSize))
                return(destSize, sourceSize)
        logging.info("total source size:"+str(sourceSize)+"  bytes, total destination size "+str(destSize))
        return(destSize, sourceSize)

    # pylint: disable=unused-variable
    # Looks like this isn't summing subdirectories?
    @staticmethod
    def getSize(startPath='/media/usb11/content'):
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
        return(total_size)

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
        free = stat.f_bavail * stat.f_frsize
        adjustedFree = free - freeSpaceCushion
        if adjustedFree< 0 : adjustedFree = 0
        return(adjustedFree)

    def moveMount(self, devMount='/dev/sda1', curMount='/media/usb0', destMount='/media/usb11'):
        '''
        This is a wrapper for umount, mount.  This is simple and works.
        we could use mount --move  if the mount points are not within a mount point that is
        marked as shared, but we need to consider the implications of non-shared mounts before
        doing it

        Find the first USB key by device
        '''
        x = ord(devMount[len(devMount)-2])
        while (not os.path.exists(devMount) and (x < ord('k'))):
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
            open('/usr/local/connectbox/brand.txt', "a") as fp:
            m = fp.read()
            if 'usb0NoMount":0' in m:
                NoMountOrig = 0                                #Hang on to the original value to restore as needed
                x = str(m).find("usb0NoMount")
                if x>0:
                    m[x+13:x+13] = "1"
                    fp.write(m)
                else:
                    fp.close()
                    logging.info("Error trying to change usb0NoMount value to 1 for copy")
                    return(False)
            else: NoMountOirg = 1                               #Hang on to the original value to restore as needed
            fp.close()
            os.sync()
            time.sleep(2)  # give time for Pause of the Mount

            y =self.unmount(curMount)
            if y > 0:
                logging.info("Error trying to  unmount "+str(curMount)+"  error: "+str(y))
            y = self.mount(devMount, destMount)
            if y > 0:
                logging.info("Error trying to  mount "+str(devMount)+"  error: "+str(y))                
            if NoMountOrig == 0:
                open('/usr/local/connectbox/brand.txt', "a") as fp:
                m = fp.read()
                if 'usb0NoMount":0' in m:
                    NoMountOrig = 0                                #Hang on to the original value to restore as needed
                    fp.close()
                    os.sync()
                    time.sleep(2)
                    return(y)
                else:
                    x = str(m).find("usb0NoMount")
                    if x > 0:
                        m[x+13:x+13] = "0"
                        fp.write()
                        fp.close()
                        os.sync()
                        return(y)
                    else:
                        logging.info("usb0NoMount not found in brand.txt")
                        fp.close()
                        return(False)
            else: NoMountOrig = 1                               #Hang on to the original value to restore as needed
                fp.close()
                time.sleep(2)  # give time for Pause of the Mount
    
        else:
            return(x)


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
        return(x)



    def getMount(self, curDev):
        '''
        This is a method of getting the mount point for the dev (ex: returns /media/usb0 for curDev /dev/sda1)
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
        return(x)


