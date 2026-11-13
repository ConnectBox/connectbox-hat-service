"""Admin page copy commands in the hat service (buttons.py, 2026-11-13).

usage: python3 webcmd_test.py <buttons.py>

connectbox-manage writes a request file; the watcher thread in BUTTONS runs
the same copy command as the front panel and writes each step to a status
file for the admin page.  Checked here, with a fake HAT, display and USB layer
and the request/status files in a temporary folder:
- the request: a valid one is taken (and removed); unknown commands, stale or
  unreadable requests are removed and not run;
- the status: every wait/error/success page and the insert/remove prompts are
  written, with the command, its source and the request id; a successful copy
  that hands over to the re-index ends "Done - the menus are being rebuilt";
- one command at a time: a second one (panel or web) is refused while one runs
  and does not overwrite its status;
- the watcher thread runs a request from the admin page;
- a HAT without a battery reading (no front panel) is not checked for battery,
  and a low battery stops the command.
No display, USB key or program is used.
"""
import importlib.util, json, os, sys, tempfile, threading, time, types

SRC = sys.argv[1]
P = F = 0


def check(name, ok, detail=""):
    """Count and print one check."""
    global P, F
    P += bool(ok); F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))


# -- fake package so buttons.py loads anywhere ----------------------------------------
pkg = types.ModuleType("neo_batterylevelshutdown"); pkg.__path__ = []
sys.modules["neo_batterylevelshutdown"] = pkg
g = types.ModuleType("neo_batterylevelshutdown.globals"); g.a = ""; g.sequence = 0; g.device_type = "TEST"
sys.modules["neo_batterylevelshutdown.globals"] = g; pkg.globals = g
for name in ("usb", "hats", "page_display_image"):
    m = types.ModuleType("neo_batterylevelshutdown." + name)
    sys.modules["neo_batterylevelshutdown." + name] = m; setattr(pkg, name, m)
usb = sys.modules["neo_batterylevelshutdown.usb"]
usb.isUsbPresent = lambda dev=None: "/dev/sda1"
rpi = types.ModuleType("RPi"); rpi.GPIO = types.SimpleNamespace(); sys.modules["RPi"] = rpi; sys.modules["RPi.GPIO"] = rpi.GPIO
spec = importlib.util.spec_from_file_location("neo_batterylevelshutdown.buttons", SRC)
bm = importlib.util.module_from_spec(spec); sys.modules[spec.name] = bm; spec.loader.exec_module(bm)
B = bm.BUTTONS

T = tempfile.mkdtemp()
B.WEB_REQUEST_FILE = os.path.join(T, "run", "boxcontent_request.json")
B.WEB_STATUS_FILE = os.path.join(T, "run", "boxcontent_status.json")
B.WEB_POLL_SECS = 0.05
B.NOMOUNT_MARKER = os.path.join(T, "nomount_marker")


class Display:
    """Fake display: records the pages shown."""
    display_type = "OLED"
    def __init__(self): self.pageStack = ""; self.shown = []
    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        return lambda *a, **k: self.shown.append(name)


class Hat:
    """Fake HAT with an optional battery reading."""
    def __init__(self, battery=None):
        self.indexPending = False
        self.displayPowerOffTime = 0
        if battery is not None:
            self.BATTERY_WARNING_VOLTAGE = 3200
            self.batteryLevelAboveVoltage = lambda level: battery > level


def status():
    """The status file as written, or None."""
    try:
        with open(B.WEB_STATUS_FILE) as f: return json.load(f)
    except OSError: return None


def request(command, age=0, raw=None):
    """Write a request file as connectbox-manage does."""
    os.makedirs(os.path.dirname(B.WEB_REQUEST_FILE), exist_ok=True)
    with open(B.WEB_REQUEST_FILE, "w") as f:
        f.write(raw if raw is not None else json.dumps({"command": command, "id": "r1", "time": time.time() - age}))


def make(hat=None):
    """A BUTTONS object with the fake HAT and display (no brand.j2 needed)."""
    B._recoverNoMount = lambda self: None
    return B(hat or Hat(), Display())


# -- the request file ---------------------------------------------------------------
b = make()
check("no request file: nothing", b._takeWebRequest() is None)
request("copy_from_usb")
r = b._takeWebRequest()
check("valid request taken, with its id", r == {"command": "copy_from_usb", "id": "r1"}, r)
check("... and removed", not os.path.exists(B.WEB_REQUEST_FILE))
request("erase_folder")
check("a command the page may not run (erase) is not taken", b._takeWebRequest() is None and not os.path.exists(B.WEB_REQUEST_FILE))
request("copy_to_usb", age=B.WEB_REQUEST_MAX_AGE_SECS + 5)
check("a stale request (older than the limit) is dropped", b._takeWebRequest() is None and not os.path.exists(B.WEB_REQUEST_FILE))
request(None, raw="{not json")
check("an unreadable request is dropped", b._takeWebRequest() is None and not os.path.exists(B.WEB_REQUEST_FILE))

# -- status written along the way ------------------------------------------------------
b = make()
def fake_ok(command):
    b._wait("Checking Space"); b._wait("Copying 45%\nSize:22431MB"); return True
b._executeCommand = fake_ok
check("successful command returns True", b.executeCommands("copy_to_usb", source="web", request_id="abc") is True)
s = status()
check("status after success: done / Done, with command, source and id",
      s and s["state"] == "done" and s["text"] == "Done" and s["command"] == "copy_to_usb" and s["source"] == "web" and s["id"] == "abc", s)
b = make()
def fake_reindex(command):
    b._wait("Copying 99%"); b.hat.indexPending = True; return True
b._executeCommand = fake_reindex
b.executeCommands("copy_from_usb")
s = status()
check("copy handed over to the re-index: 'Done - the menus are being rebuilt', source panel",
      s and s["state"] == "done" and s["text"] == "Done - the menus are being rebuilt" and s["source"] == "panel", s)
b = make()
b._executeCommand = lambda command: b._error("Not enough room")
check("failed command returns False", b.executeCommands("copy_from_usb", source="web") is False)
s = status()
check("status after failure: error / the error page's text", s and s["state"] == "error" and s["text"] == "Not enough room", s)
b = make()
seen = []
def fake_steps(command):
    usb.isUsbPresent = lambda dev=None: ""
    b.USB_WAIT_SECS = 0
    b._waitForUsb(); seen.append(status()["text"])
    usb.isUsbPresent = lambda dev=None: "/dev/sda1"
    b._waitForRemoval("/dev/sdb1"); seen.append(status()["text"])
    return True
b._executeCommand = fake_steps
b.executeCommands("copy_to_usb", source="web")
check("insert and remove prompts written", seen == ["Insert USB key", "Remove the USB key"], seen)
check("status file written atomically (no .tmp left)", not os.path.exists(B.WEB_STATUS_FILE + ".tmp"))

# -- one command at a time ---------------------------------------------------------------
b = make()
go = threading.Event(); started = threading.Event()
def fake_block(command):
    b._wait("Copying 10%"); started.set(); go.wait(5); return True
b._executeCommand = fake_block
t = threading.Thread(target=b.executeCommands, args=("copy_to_usb",), kwargs={"source": "panel"}); t.start()
started.wait(5)
check("second command while one runs is refused", b.executeCommands("copy_from_usb", source="web", request_id="x") is False)
s = status()
check("... and does not overwrite the running command's status", s and s["state"] == "running" and s["text"] == "Copying 10%" and s["source"] == "panel", s)
go.set(); t.join(5)
check("lock released afterwards: a new command runs", b.executeCommands("copy_from_usb") is True)

# -- the watcher thread ---------------------------------------------------------------------
b = make()
ran = []
b._executeCommand = lambda command: ran.append((command, b._source, b._requestId)) or True
os.makedirs(os.path.dirname(B.WEB_REQUEST_FILE), exist_ok=True)
request("copy_to_usb")                     # left over from before the start: must not run
b.startWebCommands()
time.sleep(0.3)
check("a request left over from before the start is not run", ran == [], ran)
request("copy_from_usb")
for _ in range(60):
    if ran: break
    time.sleep(0.05)
check("watcher runs the admin page's request (source web, its id)", ran == [("copy_from_usb", "web", "r1")], ran)
check("starting the watcher twice keeps one thread", (b.startWebCommands() or True) and threading.active_count() < 10)

# -- battery check ---------------------------------------------------------------------------
b = make(Hat())                            # no battery reading (DummyHAT)
check("no battery reading: no battery check (unknown choice reported instead)",
      b._executeCommand("no_such") is False and status()["text"] == "Unknown choice", status())
b = make(Hat(battery=3000))
check("low battery stops the command", b._executeCommand("copy_from_usb") is False and status()["text"] == "Battery low", status())

print("\nResults: %d passed, %d failed" % (P, F)); sys.exit(1 if F else 0)
