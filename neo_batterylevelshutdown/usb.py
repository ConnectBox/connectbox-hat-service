import logging
import os
import time
import subprocess
import shutil
import sys
import neo_batterylevelshutdown.hats as hat

#    @staticmethod
def isUsbPresent(devPath='/dev/sda1'):
    '''

    Returns if there is a USB plugged into specified devPath
    (does not depend on stick being mounted)
    :return: True / False
    '''
    y = 0
    x = devPath[-2]
    logging.info("is USB Present x is: "+x)
    while (x < "k"):                                              #scan for usb keys  a - j
        z = (os.path.exists("/dev/sd"+x+"1"))
        logging.info("at position "+x+" key is "+str(z))
        if ((z != False) and (y == 0)):
            logging.info("found  usb key at: "+x)
            return('/dev/sd'+x+"1")
        x = chr(ord(x)+1)
    return(False)                                                           #return the first USB key or 0 for none


#    @staticmethod
def unmount(curPath='/media/usb0'):
    '''
    Unmount the USB drive from curPath
    :return:  True / False
    '''
    logging.debug("Unmounting file at location %s", curPath)
    response = subprocess.call(['umount', curPath])  # unmount drive
    return(response)


#    @staticmethod
def mount(devPath='/dev/sda1', newPath='/media/usb11'):
    '''
    Mount the USB drive at the devPath to the specified newPath location
     :return: True / False
    '''
    x = ord(devPath[-2])
#   Find the first USB key in the system
    while not os.path.exists(devPath) and (x < ord('k')):
        x = ord(devPath[-2]) + 1
        devPath = "/dev/sd"+chr(x)+"1"
    logging.info("Mounting USB at %s to %s", devPath, newPath)
    if not os.path.exists(newPath):  # see if desired mounting directory exists
        os.makedirs(newPath)  # create directory and all of the intermediary directories
    response = subprocess.call(['mount',"-t", "auto", "-o", "utf8", devPath, newPath])
    logging.info("Mount Response: %s", response)
    return(response)


#    @staticmethod
def copyFiles(sourcePath='/media/usb11', destPath='/media/usb0', ext='/content/'):
    '''
    Move files from sourcePath to destPath recursively
    To do this we need to turn off automount temporarily by changing the usb0NoMount flag in brand.txt

    :param sourcePath: place where files are if it is '/media/usbX' it will copy the files from that mount and then it will loop through the
    :remaining usb's excluding to copy to the dest (/media/usb0)
    :param destPath:  where we want to copy them to
    :return:  True / False
    '''

    DISPLAY_TIMEOUT_SECS = 120
    logging.info("Copying from: "+sourcePath+" to: "+destPath)
    y = 0
    if (os.path.exists(sourcePath+ext)):
        if os.path.exists(sourcePath) and os.path.exists(destPath):
            files_in_dir = str(sourcePath+ext)
            files_to_dir = str(destPath+ext)
            if files_in_dir[-1] != "/": files_in_dir = files_in_dir + "/"
            if files_to_dir[-1] != "/": files_t0_dir = files_to_dir + "/"
            try:
                if os.path.isdir(files_in_dir):
                    hat.displayPowerOffTime = sys.maxsize
                    x = logging.info("Copying tree: "+files_in_dir+" to: "+files_to_dir)
                    shutil.copytree(files_in_dir, files_to_dir, symlinks=True, ignore_dangling_symlinks=True)
                    logging.info("Used copytree to move files")
#                   hat.displayPowerOffTime = time.time() + DISPLAY_TIMEOUT_SECS
                else:
                    hat.displayPowerOffTime = sys.maxsize
                    logging.info("Copying: "+files_in_dir+" to: "+files_to_dir)
                    x = shutil.copy2(files_in_dir, files_to_dir)
                    logging.info("used copy2 to move files")
#                   hat.displayPowerOffTime = time.time() + DISPLAY_TIMEOUT_SECS
            except OSError as err:
                logging.info("Copytree Errored out with error of OSError err: "+str(err))
                y = 1
                return(1)
            except BaseException as err:
                logging.info("Copytree Errored out with BaseException with BaseException:  err: "+str(err))
                y = 1
                return(1)
            logging.info("going to try and copy the  stats over to the target!")
        else:
            logging.info("We found the destination of the copy but there is no "+ext+" directory or source indicie is out of range")
            return(1)
    else:
        logginf.info("source path doosn't exsists, no copy possible")
        return(1)


def checkSpace( sourcePath='/media/usb11', destPath='/media/usb0'):
    '''
    Function to make sure there is space on destination for source materials
    :param sourcePath: path to the source material
    :param destPath:  path to the destination
    :param sourdest : indicates that we are copying source to destination if 1 otherwise were copying destination to source
    :return: True / False
    '''
    logging.info("Starting the Space Check "+sourcePath+" to "+destPath)
    freeSpaceCushion = 1073741824  # 1 GiB
    try:
        stat = os.statvfs(destPath)
    except:
        stat.f_bfree = 0
        stat.stat.f_bsize=0
    logging.info("Completed the os.statvfs of: "+destPath)
    free = stat.f_bfree * stat.f_bsize
    adjustedFree = free - freeSpaceCushion
    if adjustedFree< 0 : adjustedFree = 0
    logging.info("Returning free space of : "+str(adjustedFree))
    destSize = adjustedFree
    logging.info("got Destination size of :"+str(destSize))
    SourceSize = 0
    y = 0
    a = sourcePath
    if a[-1]=="/":
        a = sourcePath[-1]
    b = "/content/"
    logging.info("checking the source of : "+(a+b))
    if (os.path.exists(a+b)):
        logging.info("The source "+(a+b)+" Exsists moving on")
        total_size = 0
        total_count = 0
        for (dirpath, dirnames, filenames) in os.walk((a+b), topdown = True, onerror=None, followlinks = True):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
#                    logging.info("total size is now "+str(total_size))
                except:
                    pass
                total_count += 1
#            logging.info("Source Files completed of directory ")
        SourceSize = total_size
        logging.info("got source size as : "+str(SourceSize)+" Path is: "+(a+b))
    else:
        logging.info("source path "+a+b+" dosn't exsist so there is no length for source")
        SourceSize = 0
    logging.info("total source size:"+str(SourceSize)+"  bytes, total destination size "+str(destSize))
    return(destSize, SourceSize)

    # pylint: disable=unused-variable
    # Looks like this isn' summing subdirectories?


#    @staticmethod
def getSize( startPath='/media/usb11/content'):
    '''
    Recursively get the size of a folder structure
     :param startPath: which folder structure
    :return: size in bytes of the folder structure
    '''
    logging.info("Getting Size of: "+startPath)
    total_size = 0
    total_count = 0
    for (dirpath, dirnames, filenames) in os.walk(startPath, topdown = True, onerror=None, followlinks = True):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except:
                pass
            total_count += 1
        logging.info("File completed of directory ")
    logging.info("Total size is: "+str(total_size)+" total count of file was: "+str(total_count))
    return(total_size)
#     @staticmethod

def getFreeSpace( path='/media/usb0'):
    '''
    Determines how much free space in available for copying
    :param path: a path to put us in the right partition
    :return:  size in bytes of free space
    '''
     # this is the cushion of space we want to leave free on our internal card
    logging.info("getting free space of : "+path)
    freeSpaceCushion = 1073741824  # 1 GiB
    stat = os.statvfs(path)
    logging.info("Completed the os.statvfs(path)")
    free = stat.f_bfree * stat.f_bsize
    adjustedFree = free - freeSpaceCushion
    if adjustedFree< 0 : adjustedFree = 0
    logging.info("Returning free space of : "+str(adjustedFree))
    return(adjustedFree)


def moveMount(curMount='/media/usb0', destMount='/media/usb11'):
    '''
    This is a wrapper for umount, mount.  This is simple and works.
    we could use mount --move  if the mount points are not within a mount point that is
    marked as shared, but we need to consider the implications of non-shared mounts before
    doing it
    '''

#   Find the first USB key by device
    logging.info("Entered Move Mount with move: "+curMount+" to : "+destMount)

#    This is a method of getting the device for the mount point


# take the file mount outuput and separate it into lines
    mounts = str(subprocess.check_output(['df']))
    mounts = mounts.split("\\n")
    #take the lines and check for the mount.
    for line in mounts:
        if (curMount in line):
            logging.info("Found current mount as : "+str(line))
            x = line.split(" ", 1)
            x = x[0].rstrip(" ")
            x = ''.join(x)
            logging.info("mount is : "+x)
            break
        else:
            x = ""
    logging.info("Unmounting file at location %s", x)
    y = subprocess.call(['umount', x])  # unmount drive
    if y > 0:
        logging.info("Error trying to  unmount "+str(curMount)+"  error: "+str(y))
    else:
        logging.info("Unmount succeeded")
    b = destMount
    print("trying to do mount: " + b)
    try: # general fat mount
        res = os.system(b)				#do the mount
        print("Result of mount was: "+str(res))
        logger.info("Completed mount " + b + " result " + str(res) + " time is " + time.asctime())
    except:
        print("mount" + b + " failed result was: "+str(res))
        logger.info("mount" + b + " failed result was: "+str(res) + " time is " + time.asctime())
        if res != 0:
####################### we didn't mount fat drive try NTFS drive #######################
            try:   #try explicit ntfs mount
                if (res > 0):		#if we have res > 0 then we have an error
                    if y>= "5.15.0":
                        b = "mount /dev/" + e.group() + "-t ntfs -0 noatime, nodev, nosuid, sync, utf8" + " /media/usb" + chr(a)
                    else:
                        b = "mount /dev/" + e.group() + "-t ntfs -o noatime, nodev, nosuid, sync, iocharset=utf8" + " /media/usb" + char(a)
                    res = os.system(b)
                    print("tried new NTFS mount of: "+b + "result was: " + str(res))
                    logger.info("Retried NTFS mount of "+b+" with result of "+str(res) + " time is " + time.asctime())
            except:
                logger.info("on NTFS  mount of USB key errored")
                print("on NTFS mount of USB key errored,  res =" + str(res))
                res = -1
            if DEBUG > 2: print("completed mount /dev/",e.group)
        if res > 0: y = 1
        else: y = 0
    if y > 0:
        logging.info("Error trying to  mount "+str(x)+"  error: "+str(y))
    else:
        logging.info("Mount succeeded")
    return(y)


def getDev(curMount):
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




def getMount(curDev):
    '''
    This is a method of getting the mount point for the dev (ex: returns /media/usb0 for curDev /dev/sda1)
    '''
	# take the file mount outuput and separate it into lines
    print("getMount looking for "+str(curDev))
    mounts = str(subprocess.check_output(['df']))
    logging.info("mounts are: "+str(mounts))
    mounts = mounts.split("\\n")
    # take the lines and check for the mount.
    for line in mounts:
        if (str(curDev) in line):
            logging.info("Found line in mounts for : "+line)
            x = line.split("%", 1)
            x = x[1].rstrip(" ")
            x = x.lstrip(" ")
            x = ''.join(x)
            break
        else:
            x = ""
    logging.info("output of getMount is : "+x)
    print("output of getMount is "+x)
    return(x)


def getUSB(whatUSB):
    '''
    This is a methood of getting the x'th USB position based on what is passed
    as a number, 0=all  key, 1=first key, 2=second key, etc. if not found it returns empty string.
    '''
    mounts = str(subprocess.check_output(['ls','/dev/']))
    mounts = mounts.split("\\n")
    print ("len of mounts is: "+str(len(mounts)))
    x = 0
    y = 0
    c = ""
    for line in mounts:
        if ('sd' in line):
            print("line is: "+ line)
            logging.info("Found a device sd : ")
            x = line.find("sd")
            if ((x >= 0) and (len(line)> (x+3))):    # we look for 8 so we can return the mount not just the device
                a = line[(x+2)]
                b = line[(x+3)]
                c = c + "sd" + a + b + " "
                if ((a.isalpha()) and (b.isnumeric()) and (y == whatUSB) and (whatUSB > 0)): return(c)
            elif ((x >=0) and (len(line)>= x+3)): y +=1
    if (whatUSB == 0): return(c)
    return("")
