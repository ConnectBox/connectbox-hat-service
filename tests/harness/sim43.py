from unittest import mock
"""
Simulation tests for the hat-service admin commands, button timing and
display page logic.  Hardware (GPIO, OLED, mounts) is faked; files are real,
in temporary folders, so deletion order and copy results are checked for real.

Run: python3 sim43.py <dir with buttons.py and displays.py>
"""
import os, sys, types, shutil, tempfile, time, threading, json

SRC = sys.argv[1]
PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print("  [PASS] " + label)
    else:
        FAIL += 1; print("  [FAIL] " + label + ((": " + str(detail)) if detail else ""))


# ── fake package ────────────────────────────────────────────────────────────
pkg = types.ModuleType("neo_batterylevelshutdown"); pkg.__path__ = []
sys.modules["neo_batterylevelshutdown"] = pkg
g = types.ModuleType("neo_batterylevelshutdown.globals")
g.device_type = "TEST"; g.a = ""; g.sequence = 0; g.sequence_time = 0.0
g.screen_enable = [1] * 14
sys.modules["neo_batterylevelshutdown.globals"] = g; pkg.globals = g
hatmod = types.ModuleType("neo_batterylevelshutdown.hats")
sys.modules["neo_batterylevelshutdown.hats"] = hatmod; pkg.hats = hatmod


class FakeGPIO:
    states = {}
    @classmethod
    def input(cls, pin):
        f = cls.states.get(pin, lambda t: 1)
        return f(time.time() - cls.t0)
    t0 = 0.0
rpi = types.ModuleType("RPi"); rpi.GPIO = FakeGPIO
sys.modules["RPi"] = rpi; sys.modules["RPi.GPIO"] = FakeGPIO


class Page:
    def __init__(self, dev=None, name="", text=""):
        self.name = name; self.text = text
    def draw_page(self):
        pass


pdi = types.ModuleType("neo_batterylevelshutdown.page_display_image"); pdi.PageDisplayImage = Page
sys.modules["neo_batterylevelshutdown.page_display_image"] = pdi; pkg.page_display_image = pdi
for name, cls in [("page_none", "PageBlank"), ("page_main", "PageMain"), ("page_battery", "PageBattery"),
                  ("page_info", "PageInfo"), ("page_stats", "PageStats"), ("page_memory", "PageMemory"),
                  ("page_battery_low", "PageBatteryLow"), ("page_power_down", "PagePowerDown"),
                  ("page_multi_bat", "PageMulti_Bat")]:
    m = types.ModuleType("neo_batterylevelshutdown." + name)
    setattr(m, cls, lambda *a, **k: Page())
    sys.modules["neo_batterylevelshutdown." + name] = m; setattr(pkg, name, m)
# Internet page (2026-11-05): a real class so displays.py's isinstance() check works; not wanted
class PageInternet:
    def __init__(self, *a, **k): self._page = Page()
    def draw_page(self): return self._page.draw_page()
pi_mod = types.ModuleType("neo_batterylevelshutdown.page_internet")
pi_mod.PageInternet = PageInternet; pi_mod.wanted = lambda: False
sys.modules["neo_batterylevelshutdown.page_internet"] = pi_mod; pkg.page_internet = pi_mod
hu = types.ModuleType("neo_batterylevelshutdown.HAT_Utilities"); hu.get_device = lambda: None
sys.modules["neo_batterylevelshutdown.HAT_Utilities"] = hu
pil = types.ModuleType("PIL"); pil.Image = types.SimpleNamespace(); sys.modules["PIL"] = pil


# ── fake USB layer: one key, real folders ───────────────────────────────────
class FakeUsb(types.ModuleType):
    def reset(self, root, key_mounted_at="usb0", present=True, key_files=None, internal_files=None,
              copy_fails=False, free_internal=10**9, free_key=10**9, remove_after=0.0):
        self.root = root
        self.internal = os.path.join(root, "media", "usb0")       # internal folder (not mounted)
        self.keydir = os.path.join(root, "key")                    # the key's files
        self.admin = os.path.join(root, "media", "usb11")
        for d in (self.internal, self.keydir):
            os.makedirs(d, exist_ok=True)
        for base, files in ((self.keydir, key_files), (self.internal, internal_files)):
            for rel, data in (files or {}).items():
                p = os.path.join(base, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w").write(data)
        self.present = present
        self.mounted_at = {"usb0": self.internal, "": None, "elsewhere": os.path.join(root, "media", "usb3")}[key_mounted_at] if present else None
        self.mount_point_name = key_mounted_at if present else ""
        self.copy_fails = copy_fails
        self.free = {"internal": free_internal, "key": free_key}
        self.remove_at = (time.time() + remove_after) if remove_after else None
        self.calls = []

    # device / mount queries
    def isUsbPresent(self, devPath='/dev/sda1'):
        if self.remove_at is not None and time.time() >= self.remove_at:
            self.present = False; self.mounted_at = None
        return "/dev/sda1" if self.present else ""

    def _mp(self):
        """Mount point name of the key as the code sees it."""
        if not self.present or self.mounted_at is None:
            return ""
        if self.mounted_at == self.internal:
            return BUTTONS.INTERNAL
        if self.mounted_at == self.admin:
            return BUTTONS.ADMIN_MOUNT
        return self.mounted_at

    def getMount(self, dev):
        return self._mp()

    def getDev(self, mnt):
        return "/dev/sda1" if self._mp() == mnt and mnt != "" else ""

    def mount(self, dev, path):
        self.calls.append(("mount", path)); self.mounted_at = self.admin; return True

    def moveMount(self, cur, dest):
        self.calls.append(("moveMount", cur, dest)); self.mounted_at = self.admin; return 0

    def unmount(self, path):
        self.calls.append(("unmount", path)); self.mounted_at = None; return 0

    # paths as seen by the code -> real folders
    def real(self, path):
        if path.startswith(BUTTONS.ADMIN_MOUNT) or (self.mounted_at and path.startswith(self.mounted_at)):
            return self.keydir + path[len(BUTTONS.ADMIN_MOUNT):] if path.startswith(BUTTONS.ADMIN_MOUNT) else self.keydir + path[len(self.mounted_at):]
        if path.startswith(BUTTONS.INTERNAL):
            return self.internal + path[len(BUTTONS.INTERNAL):]
        return path

    def getSize(self, path):
        total = 0
        for d, _, fs in os.walk(self.real(path)):
            total += sum(os.path.getsize(os.path.join(d, f)) for f in fs)
        return total

    def checkSpace(self, src, dest):
        size = self.getSize(src + "/content/") if os.path.isdir(self.real(src + "/content/")) else 0
        free = self.free["key"] if dest == BUTTONS.ADMIN_MOUNT else self.free["internal"]
        return free, size

    def copyFiles(self, src, dest, ext):
        self.calls.append(("copyFiles", src, dest))
        if self.copy_fails:
            return 1
        shutil.copytree(self.real(src + ext), self.real(dest + ext), dirs_exist_ok=True)
        return 0


usb = FakeUsb("neo_batterylevelshutdown.usb")
sys.modules["neo_batterylevelshutdown.usb"] = usb; pkg.usb = usb

# ── load the code under test ────────────────────────────────────────────────
import importlib.util
def load(name):
    spec = importlib.util.spec_from_file_location("neo_batterylevelshutdown." + name, os.path.join(SRC, name + ".py"),
                                                  submodule_search_locations=None)
    mod = importlib.util.module_from_spec(spec); mod.__package__ = "neo_batterylevelshutdown"
    sys.modules["neo_batterylevelshutdown." + name] = mod; spec.loader.exec_module(mod)
    return mod

buttons = load("buttons")
BUTTONS = buttons.BUTTONS
displays = load("displays")


class FakeDisplay:
    display_type = 'OLED'
    def __init__(self):
        self.pageStack = 'admin'; self.shown = []
    def _show(self, what, text=""):
        self.shown.append((what, text))
    def showWaitPage(self, a): self._show("wait", a)
    def showErrorPage(self, a): self._show("error", a)
    def showSuccessPage(self): self._show("success")
    def showRemoveUsbPage(self, a=""): self._show("remove")
    def showInsertUsbPage(self): self._show("insert")
    def showAdminPage(self, name): self.pageStack = 'admin'; self._show("admin", name)


class FakeHat:
    USABLE_BUTTONS = [8, 10]
    BATTERY_WARNING_VOLTAGE = 3200
    def __init__(self): self.battery_ok = True; self.shutdowns = 0; self.displayPowerOffTime = 0
    def batteryLevelAboveVoltage(self, v): return self.battery_ok
    def shutdownDevice(self): self.shutdowns += 1


def make(tmp, **kw):
    BUTTONS.INTERNAL = "/media/usb0"; BUTTONS.ADMIN_MOUNT = "/media/usb11"; BUTTONS.USB_WAIT_SECS = 1
    usb.reset(tmp, **kw)
    BUTTONS.NOMOUNT_MARKER = os.path.join(tmp, "panel_nomount")
    hat = FakeHat(); disp = FakeDisplay(); b = BUTTONS(hat, disp)
    b.loader_started = 0
    b._startContentLoader = lambda: setattr(b, "loader_started", b.loader_started + 1)
    BUTTONS.PXUSBM_INDEX_SECS = 1
    BUTTONS.INTERNAL_INDEXED = os.path.join(tmp, "internal_indexed")
    open(BUTTONS.INTERNAL_INDEXED, "w").close()
    b._loaderStartedSince = lambda t0: False          # no PxUSBm in these tests unless set
    b.svc = {"kiwix": True, "kiwix_enabled": True, "log": []}
    def service(cmd):
        b.svc["log"].append(cmd)
        if cmd.startswith("is-enabled") and "kiwix" in cmd:
            return 0 if b.svc["kiwix_enabled"] else 1
        if cmd.startswith("is-active") and "kiwix" in cmd:
            return 0 if b.svc["kiwix"] else 3
        if cmd.startswith("stop kiwix"):
            b.svc["kiwix"] = False
        if cmd.startswith("start kiwix"):
            b.svc["kiwix"] = True
        return 0
    b._service = service
    usb.held_by = None
    usb.owner = b
    nomount = {"value": 0, "history": []}
    def checkReturn(val):
        old = nomount["value"]; nomount["value"] = val; nomount["history"].append(val); return old
    b.checkReturn = checkReturn
    os_makedirs = os.makedirs
    return b, hat, disp, nomount


def tree(path):
    out = {}
    for d, _, fs in os.walk(path):
        for f in fs:
            p = os.path.join(d, f); out[os.path.relpath(p, path)] = open(p).read()
    return out


def last(disp):
    return disp.shown[-1] if disp.shown else None


# BUTTONS.INTERNAL must map to a real folder for os.* calls inside the code:
# point the class paths at the fake root for file operations.
def run(b, cmd):
    # the code calls os.path / shutil on INTERNAL and ADMIN_MOUNT paths: use the real folders
    BUTTONS.INTERNAL = usb.internal; BUTTONS.ADMIN_MOUNT = usb.admin
    usb_real = usb.real
    usb.real = lambda p: p if p.startswith(usb.root) and not p.startswith(usb.admin) else (usb.keydir + p[len(usb.admin):] if p.startswith(usb.admin) else p)
    # key mounted at the admin mount point is the key folder: symlink admin -> key while mounted
    try:
        return b.executeCommands(cmd)
    finally:
        usb.real = usb_real


# Make the admin mount point a symlink to the key folder whenever "mounted" there
_orig_mount, _orig_move, _orig_unmount = usb.mount, usb.moveMount, usb.unmount
def _link():
    if os.path.islink(usb.admin): os.unlink(usb.admin)
    if os.path.isdir(usb.admin) and not os.listdir(usb.admin): os.rmdir(usb.admin)
    os.symlink(usb.keydir, usb.admin)
def _unlink():
    if os.path.islink(usb.admin): os.unlink(usb.admin)
usb.mount = lambda d, p: (_orig_mount(d, p), _link(), True)[2]
def _move(c, d):
    if usb.held_by == "kiwix" and usb.owner.svc["kiwix"]:
        return -1                      # umount: target is busy
    if usb.held_by == "other":
        return -1
    _orig_move(c, d); _link(); return 0
usb.moveMount = _move
usb.unmount = lambda p: (_orig_unmount(p), _unlink(), 0)[2]
usb._mp = (lambda self=usb: "" if (not self.present or self.mounted_at is None) else
           (BUTTONS.INTERNAL if self.mounted_at == self.internal else BUTTONS.ADMIN_MOUNT if self.mounted_at == self.admin else self.mounted_at))
usb.getMount = lambda dev: usb._mp()
usb.getDev = lambda mnt: "/dev/sda1" if mnt != "" and usb._mp() == mnt else ""
def _checkSpace(src, dest):
    c = os.path.join(src, "content")
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(c) for f in fs) if os.path.isdir(c) else 0
    free = usb.free["key"] if dest == usb.admin else usb.free["internal"]
    return free, size
usb.checkSpace = _checkSpace
usb.fstype = "ext4"
usb.fsType = lambda d: usb.fstype
usb.getSize = lambda p: sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs)
def _copy(src, dest, ext):
    usb.calls.append(("copyFiles", src, dest))
    if usb.copy_fails:
        return 1
    shutil.copytree(src + ext, dest + ext, dirs_exist_ok=True)
    return 0
usb.copyFiles = _copy
usb.getUSB = lambda n: ("sda1 " if usb.present else "")   # used by the old code only


print("\n== Copy from USB ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/new.txt": "NEW"},
                            internal_files={"content/old.txt": "OLD"}, remove_after=0.5)
    # key mounted at usb0 means the internal folder is hidden: model it as mounted elsewhere until moved
    usb.mounted_at = usb.internal
    ok = run(b, 'copy_from_usb')
    check("key at /media/usb0 (normal case): copy succeeds", ok is True, disp.shown)
    check("box content replaced by the key's", tree(os.path.join(usb.internal, "content")) == {"new.txt": "NEW"},
          tree(os.path.join(usb.internal, "content")))
    check("mount moved off /media/usb0 first", usb.calls[0][0] == "moveMount", usb.calls)
    check("ends on the 'Indexing' page, no success page of its own (main loop shows the one checkmark)",
          last(disp) == ("wait", "Indexing") and ("success", "") not in disp.shown, disp.shown)
    check("main loop told to expect the re-index; a press goes back to the admin menu",
          getattr(hat, "indexPending", False) is True and disp.pageStack == 'success', (getattr(hat, "indexPending", None), disp.pageStack))
    check("asked for the key to be removed", ("remove", "") in disp.shown)
    check("Don't Mount USB set on, then put back", nm["history"] == [1, 0], nm["history"])
    check("content re-indexed", b.loader_started == 1)
    check("admin_busy cleared", b.admin_busy is False)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/big.bin": "X" * 5000},
                            internal_files={"content/old.txt": "OLD"}, free_internal=100)
    usb.mounted_at = usb.internal
    ok = run(b, 'copy_from_usb')
    check("not enough room: fails with an error page", ok is False and last(disp) == ("error", "Not enough room"), last(disp))
    check("not enough room: box content NOT deleted", tree(os.path.join(usb.internal, "content")) == {"old.txt": "OLD"})
    check("not enough room: Don't Mount USB put back", nm["value"] == 0, nm["history"])
    check("not enough room: key unmounted again", ("unmount", usb.admin) in usb.calls, usb.calls)
    check("error page stays (pageStack error)", disp.pageStack == 'error')

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"other/x.txt": "x"},
                            internal_files={"content/old.txt": "OLD"})
    usb.mounted_at = usb.internal
    ok = run(b, 'copy_from_usb')
    check("key without /content/: error, box content kept",
          ok is False and last(disp) == ("error", "No content dir") and tree(os.path.join(usb.internal, "content")) == {"old.txt": "OLD"}, last(disp))

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/new.txt": "NEW"},
                            internal_files={"content/old.txt": "OLD"}, copy_fails=True)
    usb.mounted_at = usb.internal
    ok = run(b, 'copy_from_usb')
    check("copy fails: error page 'Failed Copy'", ok is False and last(disp) == ("error", "Failed Copy"), last(disp))
    check("copy fails: Don't Mount USB put back", nm["value"] == 0)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, present=False, internal_files={"content/old.txt": "OLD"})
    t0 = time.time(); ok = run(b, 'copy_from_usb')
    check("no key inserted: asks for one, then 'No USB key'",
          ("insert", "") in disp.shown and last(disp) == ("error", "No USB key") and ok is False, disp.shown)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"},
                            internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    ok = run(b, 'copy_from_usb')
    check("key not mounted (Don't Mount USB on): mounted at usb11 and copied",
          ok is True and usb.calls[0][0] == "mount" and tree(os.path.join(usb.internal, "content")) == {"new.txt": "NEW"}, usb.calls)


print("\n== Order with PxUSBm's removal clean-up ==")
def with_pxusbm(b, nm, tmp):
    """Fake PxUSBm: when usb0NoMount goes back to 0 it deletes its sentinel 0.6 s later."""
    events = []
    sentinel = os.path.join(tmp, "usb0_indexed"); open(sentinel, "w").close()
    BUTTONS.USB0_INDEXED = sentinel
    old_cr = b.checkReturn
    def cr(val):
        events.append(("flag", val))
        if val == 0:
            threading.Timer(0.6, lambda: (os.path.exists(sentinel) and os.remove(sentinel), events.append(("pxusbm_cleanup",)))).start()
        return old_cr(val)
    b.checkReturn = cr
    b._startContentLoader = lambda: events.append(("loader", os.path.exists(sentinel)))
    return events

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = usb.internal
    ev = with_pxusbm(b, nm, tmp)
    ok = run(b, 'copy_from_usb')
    kinds = [e[0] for e in ev]
    check("copy from USB: flag restored, PxUSBm clean-up done, THEN re-index",
          ok is True and kinds == ["flag", "flag", "pxusbm_cleanup", "loader"] and ev[-1] == ("loader", False), ev)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/k.txt": "K"},
                            internal_files={"content/a.txt": "A"}, remove_after=0.5)
    usb.mounted_at = usb.internal
    ev = with_pxusbm(b, nm, tmp)
    ok = run(b, 'erase_folder')
    kinds = [e[0] for e in ev]
    check("erase: Don't Mount USB on while waiting, re-index only after PxUSBm clean-up",
          ok is True and kinds == ["flag", "flag", "pxusbm_cleanup", "loader"] and ev[0] == ("flag", 1), ev)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/k.txt": "K"},
                            internal_files={"content/box.txt": "BOX"}, remove_after=0.5)
    usb.mounted_at = usb.internal
    ev = with_pxusbm(b, nm, tmp)
    ok = run(b, 'copy_to_usb')
    kinds = [e[0] for e in ev]
    check("copy to USB from the key the box was serving: box content re-indexed after clean-up",
          ok is True and kinds == ["flag", "flag", "pxusbm_cleanup", "loader"], ev)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/k.txt": "K"},
                            internal_files={"content/box.txt": "BOX"}, remove_after=0.5)
    usb.mounted_at = None
    ev = with_pxusbm(b, nm, tmp)
    ok = run(b, 'copy_to_usb')
    check("copy to a separate key: no re-index needed", ok is True and not any(e[0] == "loader" for e in ev), ev)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = usb.internal
    nm["value"] = 1                                   # Don't Mount USB already on in Configuration
    ev = with_pxusbm(b, nm, tmp)
    t0 = time.time(); ok = run(b, 'copy_from_usb')
    check("Don't Mount USB already on: setting kept, no wait for PxUSBm",
          ok is True and nm["value"] == 1 and time.time() - t0 < 5 and ev[-1][0] == "loader", (ev, time.time() - t0))


print("\n== Key held open (kiwix-serve / other) ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/new.txt": "NEW", "content/en/t.zim": "Z"},
                            internal_files={}, remove_after=0.5)
    usb.mounted_at = usb.internal
    usb.held_by = "kiwix"
    ok = run(b, 'copy_from_usb')
    check("kiwix-serve holding a .zim on the key: stopped, key moved, copy succeeds",
          ok is True and "stop kiwix-serve.service" in b.svc["log"] and tree(os.path.join(usb.internal, "content")) != {}, (disp.shown, b.svc["log"]))
    check("kiwix-serve started again afterwards", b.svc["kiwix"] is True and b.svc["log"][-1] == "start kiwix-serve.service", b.svc["log"])
    check("content indexing stopped before the move", b.svc["log"][0] == "stop connectbox-loader.service", b.svc["log"])

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/new.txt": "NEW"},
                            internal_files={"content/old.txt": "OLD"})
    usb.mounted_at = usb.internal
    usb.held_by = "other"
    t0 = time.time(); ok = run(b, 'copy_from_usb')
    check("key held by something else: 'USB busy' after retries, nothing deleted",
          ok is False and last(disp) == ("error", "USB busy") and tree(os.path.join(usb.internal, "content")) == {"old.txt": "OLD"}, (last(disp), time.time() - t0))
    check("kiwix-serve started again after the failure", b.svc["kiwix"] is True)
    check("Don't Mount USB put back after the failure", nm["value"] == 0)
    usb.held_by = None


print("\n== Copy to USB ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/stale.txt": "STALE"},
                            internal_files={"content/box.txt": "BOX"}, remove_after=0.5)
    usb.mounted_at = None
    ok = run(b, 'copy_to_usb')
    check("copy to USB succeeds", ok is True and last(disp) == ("success", ""), disp.shown)
    check("key's content replaced by the box's", tree(os.path.join(usb.keydir, "content")) == {"box.txt": "BOX"},
          tree(os.path.join(usb.keydir, "content")))
    check("box content untouched", tree(os.path.join(usb.internal, "content")) == {"box.txt": "BOX"})
    check("Don't Mount USB on during the copy, then put back", nm["history"] == [1, 0], nm["history"])

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/keep.txt": "KEEP"},
                            internal_files={"content/big.bin": "X" * 5000}, free_key=100)
    usb.mounted_at = None
    ok = run(b, 'copy_to_usb')
    check("not enough room on the key: error, key content NOT deleted",
          ok is False and last(disp) == ("error", "Not enough room") and tree(os.path.join(usb.keydir, "content")) == {"keep.txt": "KEEP"},
          (last(disp), tree(os.path.join(usb.keydir, "content"))))

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/keep.txt": "KEEP"}, internal_files={})
    usb.mounted_at = None
    ok = run(b, 'copy_to_usb')
    check("box has nothing: 'Nothing to copy', key untouched",
          ok is False and last(disp) == ("error", "Nothing to copy") and tree(os.path.join(usb.keydir, "content")) == {"keep.txt": "KEEP"}, last(disp))

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/k.txt": "K"},
                            internal_files={"content/box.txt": "BOX"}, remove_after=0.5)
    usb.mounted_at = usb.internal
    # while the key is mounted at usb0 the box folder is hidden; after the move it is visible again
    ok = run(b, 'copy_to_usb')
    check("key auto-mounted at /media/usb0: moved to usb11, then copied", ok is True and usb.calls[0][0] == "moveMount", usb.calls)


print("\n== Erase folder ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, present=False, internal_files={"content/a.txt": "A", "content/sub/b.txt": "B"})
    ok = run(b, 'erase_folder')
    check("no key: content folder emptied, success, re-indexed",
          ok is True and tree(os.path.join(usb.internal, "content")) == {} and last(disp) == ("wait", "Indexing") and b.loader_started == 1, disp.shown)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/k.txt": "K"},
                            internal_files={"content/a.txt": "A"}, remove_after=0.5)
    usb.mounted_at = usb.internal
    ok = run(b, 'erase_folder')
    check("key in: unmounted, waited for removal, then erased",
          ok is True and ("remove", "") in disp.shown and tree(os.path.join(usb.internal, "content")) == {} and tree(os.path.join(usb.keydir, "content")) == {"k.txt": "K"},
          disp.shown)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="elsewhere", key_files={"content/k.txt": "K"},
                            internal_files={"content/a.txt": "A"})
    ok = run(b, 'erase_folder')
    check("key never removed: 'USB not removed', nothing erased",
          ok is False and last(disp) == ("error", "USB not removed") and tree(os.path.join(usb.internal, "content")) == {"a.txt": "A"}, last(disp))

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, present=False)
    shutil.rmtree(os.path.join(usb.internal))
    os.makedirs(usb.internal)
    ok = run(b, 'erase_folder')
    check("no content folder at all: still done (nothing to erase), 'Indexing' handover", ok is True and last(disp) == ("wait", "Indexing"))


print("\n== Battery, unknown command, crash ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, present=False, internal_files={"content/a.txt": "A"})
    hat.battery_ok = False
    ok = run(b, 'erase_folder')
    check("low battery: 'Battery low' page, nothing erased",
          ok is False and last(disp) == ("error", "Battery low") and tree(os.path.join(usb.internal, "content")) == {"a.txt": "A"})
    hat.battery_ok = True
    b.copyToUsb = lambda: 1 / 0
    ok = run(b, 'copy_to_usb')
    check("unexpected exception: error page, admin_busy cleared",
          ok is False and last(disp) == ("error", "Error - see log") and b.admin_busy is False)
    check("error page: display kept on until a button is pressed (fix 43)", hat.displayPowerOffTime == sys.maxsize, hat.displayPowerOffTime)



print("\n== One loader start, Kiwix always back, presses during a wait ==")
def px_reacts(b, tmp, after=0.3):
    """Fake new PxUSBm: once the .internal_indexed marker is removed it starts the loader."""
    state = {"started_at": None, "px_loader": 0}
    def watch():
        end = time.time() + 5
        while time.time() < end:
            if not os.path.exists(BUTTONS.INTERNAL_INDEXED):
                time.sleep(after); state["started_at"] = time.monotonic(); state["px_loader"] += 1; return
            time.sleep(0.05)
    threading.Thread(target=watch, daemon=True).start()
    b._loaderStartedSince = lambda t0: state["started_at"] is not None and state["started_at"] > t0
    return state

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    st = px_reacts(b, tmp)
    t0 = time.time(); ok = run(b, 'copy_from_usb')
    check("PxUSBm indexes the box's content: loader started once (by PxUSBm), not by the front panel",
          ok is True and st["px_loader"] == 1 and b.loader_started == 0, (st, b.loader_started))
    check("...and the front panel did not wait the full fallback time", time.time() - t0 < 8, time.time() - t0)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    ok = run(b, 'copy_from_usb')               # nothing reacts: an older PxUSBm
    check("older PxUSBm (never starts it): front panel starts the loader itself, once",
          ok is True and b.loader_started == 1 and not os.path.exists(BUTTONS.INTERNAL_INDEXED), b.loader_started)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    nm["value"] = 1                            # mount checks off in Configuration: PxUSBm will not index
    t0 = time.time(); ok = run(b, 'copy_from_usb')
    check("mount checks off: front panel starts the loader at once", ok is True and b.loader_started == 1 and time.time() - t0 < 5)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    b.svc["kiwix"] = False                     # left stopped by an earlier (crashed) command
    ok = run(b, 'copy_from_usb')
    check("kiwix-serve left stopped by an earlier command: started again", b.svc["kiwix"] is True, b.svc["log"])

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    b.svc["kiwix"] = False; b.svc["kiwix_enabled"] = False
    ok = run(b, 'copy_from_usb')
    check("Kiwix not set up (not enabled): not started", b.svc["kiwix"] is False and "start kiwix-serve.service" not in b.svc["log"])

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/k.txt": "K"}, internal_files={"content/box.txt": "BOX"}, remove_after=0.5)
    usb.mounted_at = None
    ok = run(b, 'copy_to_usb')
    check("copy to a separate key: plain success page (no re-index)", ok is True and last(disp) == ("success", "") and not getattr(hat, "indexPending", False))

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp)
    ran = []
    b.executeCommands = lambda c: ran.append(c)
    b.command_to_reference = 'copy_from_usb'
    disp.pageStack = 'wait'
    b.checkPressTime = lambda ch: (0.2, 0)     # a short press
    b.BUTTON_PRESS_CLEARED_TIME = 0
    for ch in (8, 10):
        b.BUTTON_PRESS_BUSY = False; b.BUTTON_PRESS_CLEARED_TIME = 0
        b.handleButtonPress(ch)
    check("presses on a wait page do nothing (used to re-run the last command)", ran == [], ran)
    disp.pageStack = 'confirm'
    b.BUTTON_PRESS_BUSY = False; b.BUTTON_PRESS_CLEARED_TIME = 0
    b.handleButtonPress(10)
    check("...while Enter on the confirm page still runs it", ran == ['copy_from_usb'], ran)


print("\n== Copy progress on the front panel ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/new.txt": "NEW"}, internal_files={}, remove_after=0.5)
    usb.mounted_at = None
    ok = run(b, 'copy_from_usb')
    waits = [s[1] for s in disp.shown if s[0] == "wait"]
    check("copy page reads 'Copying 0%' with the size, no word 'Files'",
          any(w.startswith("Copying 0%\nSize:") and w.endswith("MB") for w in waits) and not any("Files" in w for w in waits), waits)
    check("both lines fit the display (15 characters)", all(len(l) <= 15 for w in waits for l in w.split("\n")), waits)

with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp)
    b.COPY_PROGRESS_SECS = 0.05
    needed = 22431 * 10**6
    free = [100 * 10**9]
    b._freeBytes = lambda path: free[0]
    samples = []
    real_copy = usb.copyFiles
    def slow_copy(src, dest, ext):
        for i in range(5):                        # one fifth of the data at a time
            free[0] -= needed // 5
            time.sleep(0.2); samples.append(g.a)
        return 0
    usb.copyFiles = slow_copy
    try:
        r = b._copyWithProgress("/media/usb11", "/media/usb0", needed)
    finally:
        usb.copyFiles = real_copy
    pcts = [int(s.split("%")[0].split()[-1]) for s in samples if s.startswith("Copying")]
    check("percentage climbs while the copy runs (20, 40, 60, 80 ...)", pcts[:4] == [20, 40, 60, 80], samples)
    check("never shows 100% before the copy has finished", max(pcts) <= 99, pcts)
    check("size shown on the second line", samples[0].endswith("\nSize:22431MB"), samples[0])
    last_text = g.a; time.sleep(0.3)
    check("watcher stops when the copy returns", g.a == last_text and r == 0)
print("\n== Button timing ==")
BUTTONS.CHECK_PRESS_THRESHOLD_SEC = 0.4      # scaled down from 4 s; logic is the same
def press(left, right):
    """left/right: (down_at, up_at) seconds after the first press, or None."""
    def f(spec):
        if spec is None: return lambda t: 1
        return lambda t: 0 if spec[0] <= t < spec[1] else 1
    FakeGPIO.states = {8: f(left), 10: f(right)}
    FakeGPIO.t0 = time.time()
    hat = FakeHat(); b = BUTTONS(hat, FakeDisplay())
    r = b.checkPressTime(8)
    return r, hat.shutdowns

(bt, dt), sd = press((0, 0.15), None)
check("short press: no shutdown, short time", sd == 0 and bt < 0.4 and dt == 0, (bt, dt, sd))
(bt, dt), sd = press((0, 9), None)
check("one button held alone: shutdown", sd == 1, (bt, dt, sd))
(bt, dt), sd = press((0, 9), (0.15, 9))
check("both held, second 0.15 s later: dual press, no shutdown", sd == 0 and dt >= 0.4, (bt, dt, sd))
(bt, dt), sd = press((0, 9), (0.3, 9))
check("both held, second pressed late (old code shut down here): dual press, no shutdown", sd == 0 and dt >= 0.4, (bt, dt, sd))
(bt, dt), sd = press((0, 0.9), (0.2, 0.4))
check("both pressed, second released early: no shutdown, not a dual long press", sd == 0 and dt < 0.4, (bt, dt, sd))


print("\n== Display pages ==")
pe = displays.page_enabled
g.screen_enable = [1, "0", 0, False, "false", "1", 1]
check("page_enabled: 1 on, '0' / 0 / False / 'false' off, '1' on, missing on",
      [pe(i) for i in range(8)] == [True, False, False, False, False, True, True, True], [pe(i) for i in range(8)])


class FakeHatD:
    axp = None
    displayPowerOffTime = 0
displays.time.sleep = lambda s: None
displays.OLED.drawLogo = lambda self: None
oled = displays.OLED(FakeHatD())
n = len(oled.statusPages)
g.screen_enable = [1] + ["0"] * (n - 2) + [1]
check("moveForward skips pages stored as '0'", oled._nextEnabled(0, 1) == n - 1, oled._nextEnabled(0, 1))
g.screen_enable = ["0"] * n
t0 = time.time(); r = oled._nextEnabled(3, 1)
check("all pages off: stays put, no endless loop", r == 3 and time.time() - t0 < 1)
g.screen_enable = [1] * (n - 1) + ["0"]
oled.pageStack = 'status'; oled.pages = oled.statusPages; oled.switchPages()
check("admin pages off ('0'): long press does not enter them", oled.pageStack == 'status')
g.screen_enable = [1] * n
oled.switchPages()
check("admin pages on: long press enters them", oled.pageStack == 'admin')
g.screen_enable = [1] * (n - 1) + [0]
oled.switchPages()
check("admin pages switched off meanwhile: Exit still leaves them", oled.pageStack == 'status')
oled.showAdminPage('erase_folder')
check("Cancel returns to the chosen admin item", oled._curPage is oled.adminPages[1] and oled.pageStack == 'admin')
check("display timer set on the HAT object", isinstance(FakeHatD.displayPowerOffTime, (int, float)) and oled.hat.displayPowerOffTime > 0)


print("\n== Copy to USB: FAT key and a file over 4 GB (fix 42b) ==")
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/keep.txt": "KEEP"},
                            internal_files={"content/small.txt": "S"}, free_key=10**12)
    big = os.path.join(usb.internal, "content", "big.zim")
    with open(big, "wb") as f:
        f.truncate(4 * 1024 ** 3 + 10)          # sparse: 4 GiB + 10 bytes
    usb.mounted_at = None
    usb.fstype = "vfat"
    ok = run(b, 'copy_to_usb')
    check("FAT key + 4 GB file: 'File over 4GB' before anything is copied",
          ok is False and last(disp) == ("error", "File over 4GB"), last(disp))
    check("... key content NOT deleted", tree(os.path.join(usb.keydir, "content")) == {"keep.txt": "KEEP"},
          tree(os.path.join(usb.keydir, "content")))
    check("... key held: usb0NoMount stays 1 while the key is in (fix 43)", nm["history"] == [1] and os.path.exists(BUTTONS.NOMOUNT_MARKER), nm["history"])
    check("... error page stays lit", hat.displayPowerOffTime == sys.maxsize, hat.displayPowerOffTime)
    usb.present = False; usb.mounted_at = None
    end = time.time() + 6
    while (nm["history"][-1] != 0 or os.path.exists(BUTTONS.NOMOUNT_MARKER)) and time.time() < end:
        time.sleep(0.2)
    check("... key pulled out: usb0NoMount back to 0, marker removed", nm["history"] == [1, 0] and not os.path.exists(BUTTONS.NOMOUNT_MARKER), nm["history"])
with tempfile.TemporaryDirectory() as tmp:
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={},
                            internal_files={"content/small.txt": "S"}, free_key=10**12, remove_after=0.5)
    with open(os.path.join(usb.internal, "content", "big.zim"), "wb") as f:
        f.truncate(4 * 1024 ** 3 + 10)
    usb.mounted_at = None
    usb.fstype = "exfat"
    usb.copy_check = True
    with mock.patch.object(BUTTONS.Buttons if hasattr(BUTTONS, "Buttons") else type(b), "_copyWithProgress", lambda self, s, d, n: 0):
        ok = run(b, 'copy_to_usb')
    check("exFAT key + 4 GB file: copy goes ahead", ok is True and last(disp) == ("success", ""), last(disp))
usb.fstype = "ext4"

print("\n== Fix 43: key held after a failed copy, start-up recovery ==")
with tempfile.TemporaryDirectory() as tmp:
    # the box was serving the key (at /media/usb0): a failure gives it back at once, as before
    b, hat, disp, nm = make(tmp, key_mounted_at="usb0", key_files={"content/k.txt": "K"},
                            internal_files={"content/big.bin": "X" * 5000}, free_key=100)
    ok = run(b, 'copy_to_usb')
    check("key the box was serving + failure: not held, usb0NoMount put back", ok is False and nm["history"][-1] == 0 and not b._heldDev, (last(disp), nm["history"]))
with tempfile.TemporaryDirectory() as tmp:
    # a held key, then a new command: the new command ends with the ORIGINAL value (0), not 1
    b, hat, disp, nm = make(tmp, key_mounted_at="", key_files={"content/keep.txt": "KEEP"},
                            internal_files={"content/big.bin": "X" * 5000}, free_key=100)
    usb.mounted_at = None
    ok = run(b, 'copy_to_usb')
    check("not enough room: key held", ok is False and b._heldDev == "/dev/sda1" and nm["value"] == 1, nm["history"])
    usb.free["key"] = 10**9; usb.remove_at = time.time() + 0.5
    ok = run(b, 'copy_to_usb')
    check("second try takes the hold over and succeeds", ok is True and last(disp) == ("success", ""), last(disp))
    time.sleep(2.5)
    check("... usb0NoMount ends at the original 0, marker removed, no hold left",
          nm["value"] == 0 and not os.path.exists(BUTTONS.NOMOUNT_MARKER) and not b._heldDev, (nm["history"], b._heldDev))
with tempfile.TemporaryDirectory() as tmp:
    # interrupted command: marker left with the old value; a new Buttons() puts it back
    brand = {"usb0NoMount": 1}
    g.read_brand = lambda *a, **k: dict(brand)
    g.write_brand = lambda d, *a, **k: brand.update(d)
    BUTTONS.NOMOUNT_MARKER = os.path.join(tmp, "panel_nomount")
    open(BUTTONS.NOMOUNT_MARKER, "w").write("0")
    BUTTONS(FakeHat(), FakeDisplay())
    check("start-up after an interrupted command: usb0NoMount back to 0, marker removed",
          brand["usb0NoMount"] == 0 and not os.path.exists(BUTTONS.NOMOUNT_MARKER), brand)
    brand["usb0NoMount"] = 1
    BUTTONS(FakeHat(), FakeDisplay())
    check("no marker: a usb0NoMount=1 set by someone else is left alone", brand["usb0NoMount"] == 1, brand)
print("\nResults: %d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
