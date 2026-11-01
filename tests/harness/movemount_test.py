import sys, types, importlib.util, tempfile, os
pkg = types.ModuleType("neo_batterylevelshutdown"); pkg.__path__ = []
sys.modules["neo_batterylevelshutdown"] = pkg
sys.modules["neo_batterylevelshutdown.hats"] = types.ModuleType("neo_batterylevelshutdown.hats")
spec = importlib.util.spec_from_file_location("neo_batterylevelshutdown.usb", sys.argv[1])
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
P = F = 0
def check(l, c, d=""):
    global P, F
    if c: P += 1; print("  [PASS]", l)
    else: F += 1; print("  [FAIL]", l, d)
dest = tempfile.mkdtemp() + "/usb11"
def run(fstype):
    cmds = []
    u.subprocess.check_output = lambda a: b"Filesystem 1K-blocks\\n/dev/sda1 100 50 50 50% /media/usb0\\n"
    u.subprocess.call = lambda a: cmds.append(" ".join(a)) or 0
    class Pop:
        def __init__(s, *a, **k): s.stdout = types.SimpleNamespace(close=lambda: None)
        def communicate(s): return (b"5.15.93-sunxi\n", None)
    u.Popen = Pop
    u.fsType = lambda d: fstype
    u.mountedAt = lambda d: []
    def system(c):
        cmds.append(c); return 0
    u.os.system = system
    r = u.moveMount("/media/usb0", dest)
    return r, cmds
for fs, want in (("exfat", None), ("vfat", "dosfsck"), ("ntfs", "ntfsfix"), ("ext4", None)):
    r, cmds = run(fs)
    checks = [c.split()[0] for c in cmds if c.split()[0] in ("dosfsck", "ntfsfix")]
    check("%s key: checks run = %s, then mounted" % (fs, want or "none"),
          checks == ([want] if want else []) and any(c.startswith("mount ") for c in cmds), cmds)
print("Results: %d passed, %d failed" % (P, F))
