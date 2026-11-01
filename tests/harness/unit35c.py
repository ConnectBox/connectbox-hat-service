import ast, json, os, sys, tempfile, threading, time, types, subprocess, importlib.util
from unittest import mock
W = sys.argv[1]
PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print("  [PASS] " + label)
    else: FAIL += 1; print("  [FAIL] " + label + ((": " + str(detail)) if detail else ""))

def funcs(path, names, ns):
    tree = ast.parse(open(path).read())
    body = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    mod = ast.Module(body=body, type_ignores=[])
    exec(compile(mod, path, "exec"), ns)
    return ns

print("== brand.j2: atomic write, retrying read ==")
g = funcs(W + "/globals.py", {"read_brand", "write_brand"}, {"json": json, "os": os, "time": time, "BRAND_FILE": None})
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "brand.j2")
    brand = {"Brand": "ConnectBox", "usb0NoMount": 0, "pad": "x" * 3000}
    json.dump(brand, open(path, "w"))
    def race(writer, n=3000):
        stop = [False]; bad = [0]; reads = [0]
        def reader():
            while not stop[0]:
                try:
                    with open(path) as f: json.load(f)
                except ValueError: bad[0] += 1
                reads[0] += 1
        th = threading.Thread(target=reader); th.start()
        for i in range(n):
            brand["usb0NoMount"] = i % 2; writer(brand)
        stop[0] = True; th.join()
        return bad[0], reads[0]
    def old_writer(b):
        fp = open(path, "w"); json.dump(b, fp, indent=4); fp.close()
    bad_old, r1 = race(old_writer)
    bad_new, r2 = race(lambda b: g["write_brand"](b, path))
    check("old write (open 'w' then dump): a reader sees a half-written file", bad_old > 0, (bad_old, r1))
    check("new write (temp file + rename): no reader ever sees a broken file", bad_new == 0, (bad_new, r2))
    check("new write keeps the content", json.load(open(path))["usb0NoMount"] == 1 and json.load(open(path))["Brand"] == "ConnectBox")
    os.chmod(path, 0o640); g["write_brand"](brand, path)
    check("new write keeps the file mode", oct(os.stat(path).st_mode & 0o777) == "0o640", oct(os.stat(path).st_mode & 0o777))
    check("no temp file left behind", os.listdir(d) == ["brand.j2"], os.listdir(d))
    open(path, "w").close()                                   # caught empty (mid-write)
    threading.Timer(0.3, lambda: json.dump(brand, open(path, "w"))).start()
    t0 = time.time(); got = g["read_brand"](path)
    check("read retries an empty file until it is whole", got["Brand"] == "ConnectBox" and time.time() - t0 < 2, time.time() - t0)
    open(path, "w").close()
    try:
        g["read_brand"](path, tries=3, delay=0.01); ok = False
    except ValueError:
        ok = True
    check("read gives up after its retries (caller keeps current settings)", ok)

src = open(W + "/globals.py").read()
check("globals.init keeps settings on an unreadable brand.j2 once loaded",
      "if _brand_loaded:" in src and "keeping current settings" in src and "return" in src.split("keeping current settings")[1][:80])
check("globals.init hostname update uses the atomic write", 'write_brand(js)' in src and "f.write(json.dumps(js))" not in src)
check("buttons.checkReturn uses read_brand/write_brand", "globals.write_brand(brand)" in open(W + "/buttons.py").read())

print("\n== usb.py: no file system check on a mounted key ==")
pkg = types.ModuleType("neo_batterylevelshutdown"); pkg.__path__ = []
sys.modules["neo_batterylevelshutdown"] = pkg
sys.modules["neo_batterylevelshutdown.hats"] = types.ModuleType("neo_batterylevelshutdown.hats")
spec = importlib.util.spec_from_file_location("neo_batterylevelshutdown.usb", W + "/usb.py")
usb = importlib.util.module_from_spec(spec); spec.loader.exec_module(usb)
real_open = open
def with_mounts(text):
    def fake_open(p, *a, **k):
        if p == "/proc/mounts":
            import io; return io.StringIO(text)
        return real_open(p, *a, **k)
    return mock.patch("builtins.open", side_effect=fake_open)
mounts = "/dev/mmcblk0p1 / ext4 rw 0 0\n/dev/sda1 /media/usb11 vfat rw,nodev 0 0\n/dev/sdb1 /media/My\\040Key vfat rw 0 0\n"
with with_mounts(mounts):
    check("mountedAt finds the key's mount point", usb.mountedAt("/dev/sda1") == ["/media/usb11"], usb.mountedAt("/dev/sda1"))
    check("mountedAt decodes spaces in mount points", usb.mountedAt("/dev/sdb1") == ["/media/My Key"])
    check("mountedAt: not mounted -> []", usb.mountedAt("/dev/sdc1") == [])
    with mock.patch.object(usb.os, "system", return_value=0) as sysm, mock.patch.object(usb, "fsType", return_value="vfat"):
        r = usb._check_file_system("/dev/sda1")
        check("mounted key: check skipped, reported OK, dosfsck never run", r is True and sysm.call_count == 0, sysm.call_args_list)
        r = usb._check_file_system("/dev/sdc1")
        check("unmounted key: dosfsck -a still run", r is True and sysm.call_args_list[-1][0][0] == "dosfsck -a /dev/sdc1", sysm.call_args_list)
check("moveMount uses _check_file_system (which never checks a mounted device)",
      "    _check_file_system(x)" in open(W + "/usb.py").read().replace("\r", ""))

print("\n== HAT main loop: one success page per re-index ==")
h = funcs(W + "/hats.py", {"indexingStep"}, {"os": os, "subprocess": subprocess})
with tempfile.TemporaryDirectory() as d:
    coms = os.path.join(d, "creating_menus.txt")
    h["comsFileName"] = coms
    h["globals"] = types.SimpleNamespace(a="")
    class Disp:
        def __init__(s): s.shown = []
        def showWaitPage(s, a): s.shown.append(("wait", a))
        def showSuccessPage(s): s.shown.append("success")
    class Hat:
        indexPending = False
        running = False
        def loaderRunning(s): return s.running
        def statusFileStale(s): return False   # fix 38: files here are fresh
        def usbCheckText(s): return ""       # fix 51: no USB check running
        indexingStep = h["indexingStep"]
    hat = Hat(); hat.display = Disp()
    v = False
    hat.indexPending = True; hat.running = True                  # admin command started it; no status file yet
    v = hat.indexingStep(v)
    check("pending + loader starting: no success yet", hat.display.shown == [] and v is True)
    open(coms, "w").write("Restoring from Backup...")
    v = hat.indexingStep(v)
    check("loader's status shown as a wait page", hat.display.shown == [("wait", "Restoring from Backup...")])
    os.remove(coms)
    v = hat.indexingStep(v)
    check("status file gone but loader still running: still no success", "success" not in hat.display.shown)
    hat.running = False
    v = hat.indexingStep(v); v = hat.indexingStep(v); v = hat.indexingStep(v)
    check("loader finished: exactly one success page", hat.display.shown.count("success") == 1 and v is False, hat.display.shown)
    hat.display.shown = []
    hat.indexPending = True; hat.running = False                  # loader already done before the loop looked
    v = hat.indexingStep(False)
    check("loader finished before the loop looked: still one success page", hat.display.shown == ["success"])
    hat.display.shown = []
    open(coms, "w").write("Indexing USB"); v = hat.indexingStep(False); os.remove(coms); v = hat.indexingStep(v); v = hat.indexingStep(v)
    check("plain USB insert (no admin command): wait then one success", hat.display.shown == [("wait", "Indexing USB"), "success"], hat.display.shown)
hsrc = open(W + "/hats.py").read()
check("all three main loops use indexingStep", hsrc.count("var_Indexing = self.indexingStep(var_Indexing)") == 3)
print("Results: %d passed, %d failed" % (PASS, FAIL))
