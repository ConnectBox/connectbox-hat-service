import logging
import os
import time
import subprocess
import shutil
import sys
from subprocess import Popen, PIPE
import neo_batterylevelshutdown.hats as hat


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#    @staticmethod
# File systems that store Unix permissions (Linux formats).  They reject the
# FAT-only utf8 mount option and are not checked with dosfsck/ntfsfix.
# (Same list and rules as PxUSBm.py.)
POSIX_FILESYSTEMS = ('ext2', 'ext3', 'ext4', 'xfs', 'btrfs', 'f2fs')


def fsType(dev_path):
    """File system type of a device (e.g. 'vfat', 'ext4'), or '' if none / unknown."""
    try:
        out = subprocess.run(['lsblk', '-dno', 'FSTYPE', dev_path],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, timeout=10).stdout
        return out.strip()
    except Exception:
        return ''


def _hasPartitions(letter):
    """True if /dev/sd<letter> has any numbered partition (/dev/sdb1, /dev/sdb2 ...)."""
    return any(os.path.exists('/dev/sd' + letter + str(n)) for n in range(1, 10))


def isUsbPresent(devPath='/dev/sda1'):
    '''
    Find a USB key, starting at the drive letter of devPath (/dev/sdb1 or
    /dev/sdb -> 'b') and looking up to /dev/sdj.  A key is its first
    partition (/dev/sdX1, the usual case) or, for a stick formatted with no
    partition table (mkfs.ext4 /dev/sdX), the whole disk /dev/sdX when that
    has a file system.  Does not depend on the key being mounted.
    :return: the key's device path, or "" if none
    '''
    import re
    m = re.search(r'sd([a-z])', devPath or '')
    start = ord(m.group(1)) if m else ord('a')
    for x in range(start, ord('k')):
        letter = chr(x)
        if os.path.exists('/dev/sd' + letter + '1'):
            return '/dev/sd' + letter + '1'
        whole = '/dev/sd' + letter
        if os.path.exists(whole) and not _hasPartitions(letter) and fsType(whole) != '':
            return whole
    return ""


#    @staticmethod
def unmount(curPath='/media/usb0'):
    '''
    Unmount the USB drive from curPath
    :return:  True / False
    '''
    logging.debug("Unmounting file at location %s", curPath)
    response = subprocess.call(['umount', curPath])  # unmount drive
    return(response)

#  Mount Command based on gemini
#  returns True on success or False on Failure

def mount(dev_path='/dev/sda1', new_path='/media/usb11'):
    '''
    Mount the USB drive at the dev_path to the specified new_path location
    :return: True on success, False on failure
    '''
    apath = isUsbPresent(dev_path)
    if apath == "":
        logging.error(f"Device {dev_path} is not present.")
        return False
    else: dev_path = apath

    logging.info(f"Starting mount of {dev_path} to {new_path}")

    try:
        df_output = subprocess.check_output(['df']).decode('utf-8').splitlines()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get disk information: {e}")
        return False

    existing_mount_point = _get_existing_mount_point(df_output, apath, new_path)
    if existing_mount_point:
        return existing_mount_point

    if not os.path.exists(new_path):
        try:
            os.makedirs(new_path)  # Use makedirs for creating nested directories
            logging.info(f"Created directory: {new_path}")
        except OSError as e:
            logging.error(f"Failed to create directory {new_path}: {e}")
            return False

    fsck_result = _check_file_system(apath)
    if fsck_result is False:
        return False  # check_file_system already logs

    mount_command = _get_mount_command(apath, new_path)

    try:
        subprocess.check_call(mount_command, shell=True)
        logging.info(f"Successfully mounted {dev_path} to {new_path}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to mount {dev_path} to {new_path}: {e}")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred during mount: {e}")
        return False

def _get_existing_mount_point(df_output, dev_path, new_path):
    """
    Checks if the device is already mounted, or if the new mount point is in use.
    Returns the existing mount point if found, False otherwise.
    """
    for line in df_output:
        if dev_path in line:
            parts = line.split()
            if len(parts) > 5:
                existing_mount_point = parts[5]
                print("Device (dev_path) is already mounted at (existing_mount_point)",dev_path, existing_mount_point)
                logging.info(f"Device {dev_path} is already mounted at {existing_mount_point}",dev_path,existing_mount_point)
                if new_path in existing_mount_point:
                    return True
                else:
                    return False
            else:
                logging.warning(f"Unexpected df output format for {dev_path}: {line}",dev_path, line) #handle edge case
                return False

        elif new_path in line:
            print("Mount point (new_path) is already in use")
            logging.warning(f"Mount point {new_path} is already in use.")
            return False
    return False

def mountedAt(dev_path):
    """Mount points of a device from /proc/mounts (empty list if not mounted)."""
    try:
        real = os.path.realpath(dev_path)
        with open('/proc/mounts', encoding='utf-8') as f:
            return [line.split()[1].replace('\\040', ' ') for line in f
                    if line.split() and os.path.realpath(line.split()[0]) == real]
    except OSError:
        return []


def _check_file_system(dev_path):
    """
    Check and repair the key's file system before it is mounted, with the
    tool for its type: dosfsck -a for FAT, ntfsfix -d for NTFS; nothing for
    exFAT, Linux file systems or an unknown type.  Returns True unless the
    check could not be run at all: whether the key is usable is decided by
    the mount that follows, not by the checker's exit code.

    (It used to run dosfsck on every non-Linux key and treat its exit code 1
    as a failure.  Exit code 1 means "errors found and corrected", so a FAT
    key whose free-space count dosfsck had just fixed was refused - ntfsfix
    was then tried on it, failed, and the copy stopped with "USB not
    mounted" (.200, 2026-10-27).  An exFAT key went the same way.)

    Never on a mounted device: Linux marks a mounted FAT key "dirty", so
    dosfsck -a "repairs" it while it is in use (seen on a test box, with
    ntfsfix then refusing and the mount reported as failed).
    """
    where = mountedAt(dev_path)
    if where:
        logging.warning("%s is mounted at %s: file system check skipped", dev_path, ", ".join(where))
        return True
    fstype = fsType(dev_path)
    if fstype in ('vfat', 'msdos', 'fat', 'fat12', 'fat16', 'fat32'):
        command, ok_codes = "dosfsck -a " + dev_path, (0, 1)   # 1 = errors found and corrected
    elif fstype == 'ntfs':
        command, ok_codes = "ntfsfix -d " + dev_path, (0,)
    else:
        logging.info(f"{dev_path} is {fstype or 'of unknown type'}: no file system check")
        return True
    start_time = time.time()
    logging.info(f"Checking file system with: {command}")
    try:
        res = os.system(command)
    except Exception as e:
        logging.error(f"Failed to check file system on {dev_path}: {e}")
        return False
    code = res >> 8 if res > 255 else res
    if code in ok_codes:
        logging.info(f"{command}: exit {code} (ok) in {time.time() - start_time:.2f} seconds")
    else:
        logging.warning(f"{command}: exit {code} in {time.time() - start_time:.2f} seconds; trying the mount anyway")
    return True

def _get_mount_command(dev_path, mount_point):
    """
    (No "sync" option: it makes large copies to a key very slow.  The admin
    commands flush with os.sync() and unmount before asking for the key.)
    Constructs the appropriate mount command based on the kernel version.

    Returns the mount command string.
    """
    uname_result = Popen(["uname", "-r"], stdout=PIPE)
    kernel_version = uname_result.communicate()[0].decode('utf-8').strip()

    device_name = os.path.basename(dev_path)  # Extract "sda1" from "/dev/sda1"
    fstype = fsType(dev_path)
    if fstype in POSIX_FILESYSTEMS:          # Linux file systems: own type, no utf8 option
        return f"mount /dev/{device_name} -t {fstype} -o noatime,nodev,nosuid {mount_point}"
    if kernel_version >= "5.15.0":
        mount_command = f"mount /dev/{device_name} -t auto -o noatime,nodev,nosuid,utf8 {mount_point}"
    else:
        mount_command = f"mount /dev/{device_name} -t auto -o noatime,nodev,nosuid,iocharset=utf8 {mount_point}"
    return mount_command


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
    print("Copying from: "+sourcePath+" to: "+destPath)
    y = 0
    if (os.path.exists(sourcePath+ext)):
        if os.path.exists(sourcePath) and os.path.exists(destPath):
            files_in_dir = str(sourcePath+ext)
            files_to_dir = str(destPath+ext)
            if files_in_dir[-1] != "/": files_in_dir = files_in_dir + "/"
            if files_to_dir[-1] != "/": files_to_dir = files_to_dir + "/"
            if (not(os.path.isdir(files_to_dir)) and os.path.isdir(destPath)):
                 try:
                     os.mkdir(files_to_dir)
                 except:
                     print(" we had a direcrectory create on the USB key that failed.")
            try:
                if os.path.isdir(files_in_dir):
                    hat.displayPowerOffTime = sys.maxsize
                    x = print("Copying tree: "+files_in_dir+" to: "+files_to_dir)
                    shutil.copytree(files_in_dir, files_to_dir, symlinks=True, ignore_dangling_symlinks=True, dirs_exist_ok=True)
                    print("Used copytree to move files")
#                    hat.displayPowerOffTime = time.time() + DISPLAY_TIMEOUT_SECS
                    return(0)
                else:
                    hat.displayPowerOffTime = sys.maxsize
                    print("Copying: "+files_in_dir+" to: "+files_to_dir)
                    x = shutil.copy2(files_in_dir, files_to_dir, follow_symlinks = True)
                    print("used copy2 to move files")
#                    hat.displayPowerOffTime = time.time() + DISPLAY_TIMEOUT_SECS
                    return(0)
            except OSError as err:
                print("Copytree Errored out with error of OSError err: "+str(err))
                y = 1
                return(1)
            except BaseException as err:
                print("Copytree Errored out with BaseException with BaseException:  err: "+str(err))
                y = 1
                return(1)
        else:
            print("We found the destination of the copy but there is no "+ext+" directory or source indicie is out of range")
            return(1)
    else:
        logging.info("source path doesn't exist, no copy possible")
        return(1)


def checkSpace( sourcePath='/media/usb11', destPath='/media/usb0'):
    '''

    Function to make sure there is space on destination for source materials
    :param sourcePath: path to the source material
    :param destPath:  path to the destination
    :param sourdest : indicates that we are copying source to destination if 1 otherwise were copying destination to source
    :return: True / False
    '''

    print("Starting the Space Check "+sourcePath+" to "+destPath)
    freeSpaceCushion = 1073741824  # 1 GiB
    try:
        stat = os.statvfs(destPath)
        free = stat.f_bfree * stat.f_bsize
        adjustedFree = free - freeSpaceCushion
    except:
        free = 0
        adjustedFree = free - freeSpaceCushion
    print("Completed the os.statvfs of: "+destPath)
    if adjustedFree< 0 : adjustedFree = 0
    print("Returning free space of : "+str(adjustedFree))
    destSize = adjustedFree
    print("got Destination size of :"+str(destSize))
    SourceSize = 0
    y = 0
    a = sourcePath
    if a[-1]=="/":
        a = sourcePath[:-1]
    b = "/content/"
    print("checking the source of : "+(a+b))
    if (os.path.exists(a+b)):
        print("The source "+(a+b)+" Exsists moving on")
        total_size = 0
        total_count = 0
        for (dirpath, dirnames, filenames) in os.walk((a+b), topdown = True, onerror=None, followlinks = True):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
#                    print("total size is now "+str(total_size))
                except:
                    pass
                total_count += 1
#            print("Source Files completed of directory ")
        SourceSize = total_size
        print("got source size as : "+str(SourceSize)+" Path is: "+(a+b))
    else:
        print("source path "+a+b+" dosn't exsist so there is no length for source")
        SourceSize = 0
    print("total source size:"+str(SourceSize)+"  bytes, total destination size "+str(destSize))
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
    print("Getting Size of: "+startPath)
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
        print("File completed of directory ")
    print("Total size is: "+str(total_size)+" total count of file was: "+str(total_count))
    return(total_size)
#     @staticmethod

def getFreeSpace( path='/media/usb0'):
    '''
    Determines how much free space in available for copying
    :param path: a path to put us in the right partition
    :return:  size in bytes of free space
    '''
     # this is the cushion of space we want to leave free on our internal card
    print("getting free space of : "+path)
    freeSpaceCushion = 1073741824  # 1 GiB
    stat = os.statvfs(path)
    print("Completed the os.statvfs(path)")
    free = stat.f_bfree * stat.f_bsize
    adjustedFree = free - freeSpaceCushion
    if adjustedFree< 0 : adjustedFree = 0
    print("Returning free space of : "+str(adjustedFree))
    return(adjustedFree)


def moveMount(curMount='/media/usb0', destMount='/media/usb11'):
    '''
    This is a wrapper for umount, mount.  This is simple and works.
    we could use mount --move  if the mount points are not within a mount point that is
    marked as shared, but we need to consider the implications of non-shared mounts before
    doing it

    Returns "" on error else
    returns destMount on success
    '''

    DEBUG = 2
#   Find the first USB key by device
    print("Entered Move Mount with move: "+curMount+" to : "+destMount)

#    This is a method of getting the device for the mount point


# take the file mount outuput and separate it into lines
    mounts = str(subprocess.check_output(['df']))
    mounts = mounts.split("\\n")
    #take the lines and check for the mount.
    for line in mounts:
        if (curMount in line):
            print("Found current mount as : "+str(line))
            x = line.split(" ", 1)
            x = x[0].rstrip(" ")
            x = ''.join(x)
            print("mount is : "+x)
            break
        else:
            x = ""
    print("Unmounting file at location %s", x)
    y = subprocess.call(['umount', x])  # unmount drive
    if y > 0:
        print("Error trying to  unmount "+str(curMount)+"  error: "+str(y))
        return(-1)
    else:
        pass
    print("trying to do mount: " + destMount, x)
    a = str(destMount)[len(destMount)-2:]
    if not(a.isnumeric()):
        a = str(destMount)[-1]
        if not(a.isnumeric()): 
            print("we couldn't find the number on the mount")
            return(-1)
    a = int(a)
    # a is now the numeric character of the desired mount.
# Now we know we need to do a mount and have found the lowest mount point to use in (a)
    if not (os.path.exists(destMount)):  #if the /mount/usbx isn't there create it
        res = os.system("mkdir "+ destMount)
        if DEBUG > 2: print("created new direcotry ",destMount)
    z = Popen(["uname", "-r"], stdout=PIPE)
    y = str(z.communicate()[0])
    z.stdout.close()
    fstype = fsType(x)
    if fstype in POSIX_FILESYSTEMS:          # Linux file systems: own type, no utf8 option
        b = "mount " + x + " -t " + fstype + " -o noatime,nodev,nosuid " + destMount
    elif y>="5.15.0":
        b = "mount " + x + " -t auto -o noatime,nodev,nosuid,utf8 " + destMount
    else:
        b = "mount " + x + " -t auto -o noatime,nodev,nosuid,iocharset=utf8 " + destMount
    # File system check with the right tool for the key's type (dosfsck for
    # FAT, ntfsfix for NTFS, nothing for exFAT or Linux file systems, never on
    # a mounted device); the mount below decides whether the key is usable.
    # (This used to run dosfsck on every non-Linux key and ntfsfix whenever
    # dosfsck returned 1, which on an exFAT key only produced errors in the log.)
    _check_file_system(x)

###################### OK try a FAT mount now on the key ############################################
    print("trying to do mount: " + b)
    try: # general fat mount
        res = os.system(b)				#do the mount
        print("Result of mount was: "+str(res))
        print("Completed mount " + b + " result " + str(res) + " time is " + time.asctime())
    except Exception:
        print("mount" + b + " failed time is " + time.asctime())
        res = -1
    if res == 0:
        return(0)
    if fstype in POSIX_FILESYSTEMS:
        print("Error trying to mount " + x + " (" + fstype + ")")
        return(-1)
####################### we didn't mount fat, try NTFS mount #######################
    try:   #try explicit ntfs mount
        if y>= "5.15.0":
            b = "mount " + x + " -t ntfs -o noatime,nodev,nosuid,utf8 " + destMount
        else:
            b = "mount " + x + " -t ntfs -o noatime,nodev,nosuid,iocharset=utf8 " + destMount
        res = os.system(b)
        print("Retried NTFS mount of "+b+" with result of "+str(res) + " time is " + time.asctime())
    except Exception:
        print("on NTFS mount of USB key errored")
        res = -1
    if res != 0:
        print("Error trying to  mount "+str(x)+"  error: "+str(y))
        return(-1)
    else:
        print("Mount succeeded")
    return(0)


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
    mounts = mounts.split("\\n")
    # take the lines and check for the mount.
    for line in mounts:
        if (str(curDev) in line):
            print("Found line in mounts for : "+line)
            x = line.split("%", 1)
            x = x[1].rstrip(" ")
            x = x.lstrip(" ")
            x = ''.join(x)
            break
        else:
            x = ""
    print("output of getMount is : "+x)
    return(x)


def getUSB(whatUSB):
    '''
    This is a methood of getting the x'th USB position based on what is passed
    as a number, 0=all  key, 1=first key, 2=second key, etc. if not found it returns empty string.
    '''
    mounts = str(subprocess.check_output(['ls','/dev/']))
    mounts = mounts.split("\\n")
    x = 0
    y = 0
    c = ""
    print("Looking for a line with sdx1")
    for line in mounts:
        if ('sd' in line):
            print("line is: "+ line)
            x = line.find("sd")
            if ((x >= 0) and (len(line)> (x+3))):    # we look for 8 so we can return the mount not just the device
                a = line[(x+2)]
                b = line[(x+3)]
                c = c + "sd" + a + b + " "
                if ((a.isalpha()) and (b.isnumeric()) and (y == whatUSB) and (whatUSB > 0)):
                   print("found a USB drive "+c)
                   return(c)
            elif ((x >=0) and (len(line)>= x+3)): y +=1
    if (whatUSB == 0): return(c)
    return("")
