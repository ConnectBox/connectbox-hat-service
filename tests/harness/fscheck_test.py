import sys, types, importlib.util
pkg = types.ModuleType("neo_batterylevelshutdown"); pkg.__path__ = []
sys.modules["neo_batterylevelshutdown"] = pkg
sys.modules["neo_batterylevelshutdown.hats"] = types.ModuleType("neo_batterylevelshutdown.hats")
path = sys.argv[1]
spec = importlib.util.spec_from_file_location("neo_batterylevelshutdown.usb", path)
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
P = F = 0
def check(l, c, d=""):
    global P, F
    if c: P += 1; print("  [PASS]", l)
    else: F += 1; print("  [FAIL]", l, d)
def run(fstype, codes, mounted=()):
    ran = []
    u.mountedAt = lambda d: list(mounted)
    u.fsType = lambda d: fstype
    it = iter(codes)
    def fake(cmd):
        ran.append(cmd.split()[0]); return next(it)
    u.os.system = fake
    return u._check_file_system("/dev/sda1"), ran
r, ran = run("vfat", [256]); check("FAT, dosfsck exit 1 (corrected): accepted, no ntfsfix", r is True and ran == ["dosfsck"], ran)
r, ran = run("vfat", [0]); check("FAT clean: accepted", r is True and ran == ["dosfsck"])
r, ran = run("vfat", [1024]); check("FAT, dosfsck exit 4: mount still tried", r is True and ran == ["dosfsck"])
r, ran = run("ntfs", [0]); check("NTFS: ntfsfix only", r is True and ran == ["ntfsfix"], ran)
r, ran = run("ntfs", [256]); check("NTFS, ntfsfix fails: mount still tried", r is True and ran == ["ntfsfix"])
r, ran = run("exfat", []); check("exFAT: no check", r is True and ran == [])
r, ran = run("ext4", []); check("ext4: no check", r is True and ran == [])
r, ran = run("vfat", [], mounted=["/media/usb0"]); check("mounted: never checked", r is True and ran == [])
print("Results: %d passed, %d failed" % (P, F))
