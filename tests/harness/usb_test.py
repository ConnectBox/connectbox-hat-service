import sys, types, os, importlib.util
pkg = types.ModuleType("neo_batterylevelshutdown"); pkg.__path__ = []
sys.modules["neo_batterylevelshutdown"] = pkg
sys.modules["neo_batterylevelshutdown.hats"] = types.ModuleType("neo_batterylevelshutdown.hats")
spec = importlib.util.spec_from_file_location("neo_batterylevelshutdown.usb", sys.argv[1])
usb = importlib.util.module_from_spec(spec); spec.loader.exec_module(usb)
P = F = 0
def check(l, c, d=""):
    global P, F
    if c: P += 1; print("  [PASS] " + l)
    else: F += 1; print("  [FAIL] " + l + " " + str(d))
real_exists = os.path.exists
def setup(devs, fstypes):
    usb.os.path.exists = lambda p: p in devs if p.startswith("/dev/") else real_exists(p)
    usb.fsType = lambda d: fstypes.get(d, "")
setup({"/dev/sda"}, {"/dev/sda": "ext4"})
check("whole-disk ext4 key (the test box's key) found as /dev/sda", usb.isUsbPresent() == "/dev/sda", usb.isUsbPresent())
check("found when asked for /dev/sda itself", usb.isUsbPresent("/dev/sda") == "/dev/sda")
setup({"/dev/sda", "/dev/sda1"}, {"/dev/sda1": "vfat"})
check("partitioned key: first partition /dev/sda1", usb.isUsbPresent() == "/dev/sda1")
setup({"/dev/sda"}, {})
check("blank disk (no file system, no partitions): not a key", usb.isUsbPresent() == "")
setup({"/dev/sda", "/dev/sda2"}, {"/dev/sda2": "vfat", "/dev/sda": ""})
check("disk with only a 2nd partition: whole disk not used", usb.isUsbPresent() == "")
setup({"/dev/sda1", "/dev/sdb"}, {"/dev/sdb": "ext4", "/dev/sda1": "vfat"})
check("scan from /dev/sdb finds the whole-disk sdb", usb.isUsbPresent("/dev/sdb1") == "/dev/sdb")
setup(set(), {})
check("nothing plugged in: \"\"", usb.isUsbPresent() == "")
usb.fsType = lambda d: "ext4"
check("ext4 mount command: own type, no utf8", "-t ext4 -o noatime,nodev,nosuid /media/usb11" in usb._get_mount_command("/dev/sda", "/media/usb11"))
usb.fsType = lambda d: "vfat"
check("FAT mount command keeps utf8", "utf8" in usb._get_mount_command("/dev/sda1", "/media/usb11"))
usb.fsType = lambda d: "ext4"
check("ext4: no dosfsck/ntfsfix check", usb._check_file_system("/dev/sda") is True)
print("Results: %d passed, %d failed" % (P, F)); sys.exit(1 if F else 0)
