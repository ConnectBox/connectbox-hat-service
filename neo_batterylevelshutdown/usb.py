import logging
import os
import time
import subprocess
import shutil
import sys
import neo_batterylevelshutdown.hats  as hat
import neo_batterylevelshutdown.displays as display
from neo_batterylevelshutdown.globals import *


#    @staticmethod
def isUsbPresent(devPath ='/dev/sda1'):
    '''

    Returns if there is a USB plugged into specified devPath
    (does not depend on stick being mounted)
    :return: True / False
    '''
    x = devPath[-2]
    logging.info("is USB Present x is: "+x)
    while (x < "k"):                                              #scan for usb keys  a - j
        z = (os.path.exists("/dev/sd"+x+"1"))
        logging.info("at position "+x+" key is "+str(z))
        if (z != False):
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
    response = 0
    x = ord(devPath[-2])
#   Find the first USB key in the system
    while not os.path.exists(devPath) and (x < ord('k')):
        x = ord(devPath[-2]) + 1
        devPath = "/dev/sd"+chr(x)+"1"
    logging.info("Mounting USB at %s to %s", devPath, newPath)
    if not os.path.exists(newPath):  # see if desired mounting directory exists
        print ("directory path needed is "+newPath)
        os.mkdir(newPath)  # create directory and all of the intermediary directories
    x = os.system("uname -r")
    y = str(x)
    logging.info("the output of the current revision is: "+y)
    if y>="5.15.0":
       b = "mount " + devPath + " -t auto -o noatime,nodev,nosuid,sync,utf8" + newPath
    else:
       b = "mount " + devPath + " -t auto -o noatime,nodev,nosuid,sync,iocharset=utf8" + newPath
       c = "dosfsck -a " + devPath
       starttime = time.time()
       print("checking the files system before mount with: "+ c)
       try:
           res = os.system(c)                          #do a file system check befor the mount.  if it is corrupted we will get a system stop PxUSBm
           if res ==256:
               print("failed to do dosfsck -a /dev/" + devPath)
               c = "ntfsfix -d " + devPath
               try:
                   res = os.system(c)
               except:
                   print("failed to do ntfsfix -f")
                   logging.info("Failed to do ntfsfix -d on "+ devPath)
                   response = 1
           else: response = 0
       except:
           print ("Failed to do dosfsck")
           logging.info("Failed to do Dosfsck on " + devPath)
           response = 1
    if response == 0:
       response = os.system(b)                              #do the mount
    logging.info("Mount Response: %s", response)
    return(response)


#    @staticmethod
def copyFiles(sourcePath='/media/usb11', destPath='/media/usb0', ext='/content/', disp=''):
    '''
    Move files from sourcePath to destPath recursively
    To do this we need to turn off automount temporarily by changing the usb0NoMount flag in brand.txt

    :param sourcePath: place where files are if it is '/media/usbX' it will copy the files from that mount and then it will loop through the
    :remaining usb's excluding to copy to the dest (/media/usb0)
    :param destPath:  where we want to copy them to
    :return:  True / False
    '''

    handler = logging.handlers.WatchedFileHandler( os.environ.get("LOGFILE", "/var/log/neo-batteryshutdown.log"))
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(os.environ.get("LOGLEVEL", "INFO"))
    logger.addHandler(handler)

    logging.info("entering the copyFiles utility")


    comsFileName = "/usr/local/connectbox/creating_menus.txt"

    DISPLAY_TIMEOUT_SECS = 120
    logging.info("Copying from: "+sourcePath+" to: "+destPath+"with ext of: "+ ext)
    y = 0
    if sourcePath[len(sourcePath)-1] == "/":
        if len(ext)>0:
            if ext[0] == "/": ext = ext[1:]
    elif len(ext)>0:
        if ext[0] != '/':
            ext = '/' + ext
    if os.path.exists(sourcePath) and os.path.exists(destPath):
        if (os.path.exists(sourcePath+ext)):
            if len(ext)>0:
                if ((ext[0] != "/") and (destPath[len(destPath)-1] != "/")):
                        destPath = destPath + "/"
                elif ((ext[0] == "/") and (destPath[len(destPath)-1] == "/")):
                        destPaht = destPath[0:(len(destPaht)-2)]
            files_in_dir = str(sourcePath+ext)
            files_to_dir = str(destPath+ext)
            if files_in_dir[-1] != "/": files_in_dir = files_in_dir + "/"
            if files_to_dir[-1] != "/": files_t0_dir = files_to_dir + "/"
            errmd = False

            try:
                logging.info("starting the for loop on the copy")
                for path, dirs,files in os.walk(files_in_dir):
                    shortPath = path.replace((sourcePath+ext),"")
                    logging.info("shortpath is: "+ str(shortPath))
                    if len(files)>0:
                        try:
                                start_time = time.time()
                                total_size = 0.0
                                for file1 in files:
                                    total_size =+ os.path.getsize(path + "/" + file1)
                                    shutil.copy2((path + "/" + file1), (files_to_dir+shortPath), follow_symlinks=False)
                                total_time = time.time()-start_time
                                copyspeed =  total_size/total_time
                                logger.info("Completed the copy of: " + shortPath)
                                print("copyspeed is: "+(str(copyspeed)))
                                display.showWaitPage(globals.a + chr(10) + "spd:" + copyspeed)
                        except:
                                print("Had error generated in file copy loop ",file1, path, dirs, len(files))
                                logging.info("Had error generated in file copy loop", file1, path, dirs, len(files))
                                errmd = True
                                return(1)

            except:
                print ("We errored out on the file copy loop ",path, dirs, len(files))
                logging.ingo("We errored out on the file copy loop ", path, dirs, len(files))
                errmd = True
                return(1)

            try:
                os.system("rm "+ comsFileName)
            except:
                pass
        else:
            logging.info("the sourcePath+ext whic is: "+str(sourcePath + ext)+" didn't exsist")
    else:
        logging.info("our sourePath or destPath didn't exsist")
        return(1)

    return(0)


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
    if len(a)>2:
        if a[-1]=="/":
            a = sourcePath[-1]
    else:
        logging.info("source path is not valid: "+ sourcePath)
        return -1, -1
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
    if x != "":
        y = subprocess.call(['umount', x])  # unmount drive
        if y > 0:
            logging.info("Error trying to  unmount "+str(curMount)+"  error: "+str(y))
            return(0)
    else:
        logging.info("Unmount succeeded or wasn't mounted")
        y = os.system("uname -r")
    if str(y) >= "5.15.0":
        b = "mount " + x + " -t auto -o noatime,nodev,nosuid,sync,utf8" + destMount
    else:
        b = "mount " + x + " -t auto -o noatime,nodev,nosuid,sync,iocharset=utf8" + destMount
    c = "dosfsck -a " + x
    starttime = time.time()
    print("checking the files system before mount with: "+ c)
    try:
        res = os.system(c)                          #do a file system check befor the mount.  if it is corrupted we will get a system stop PxUSBm
        if res ==256:
            print("failed to do dosfsck -a /dev/" + x)
            c = "ntfsfix -d " + x
            try:
                res = os.system(c)
            except:
                print("failed to do ntfsfix -f")
                logging.info("Failed to do ntfsfix -d on "+ x)
                response = 1
        else: response = 0
    except:
        print ("Failed to do dosfsck")
        logging.info("Failed to do Dosfsck on " + x)
        response = 1
    if response == 0:
       response = os.system(b)                              #do the mount
    logging.info("Mount Response: %s", response)
    y = subprocess.call(['mount',"-t", "auto", "-o", "utf8", x, destMount])
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
    mounts = str(subprocess.check_output(['df']))
    logging.info("mounts are: "+str(mounts))
    mounts = mounts.split("\\n")
    # take the lines and check for the mount.
    for line in mounts:
        if (curDev in line):
            logging.info("Found line in mounts for : "+line)
            x = line.split("%", 1)
            x = x[1].rstrip(" ")
            x = x.lstrip(" ")
            x = ''.join(x)
            break
        else:
            x = ""
    logging.info("output of getMount is : "+x)
    return(x)



