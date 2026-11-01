"""Fix 51: front panel shows PxUSBm's "Checking USB".  usage: python3 test51_hats.py <hats.py>"""
import ast, os, sys, tempfile, time, types, logging, subprocess
HATS = sys.argv[1]; P = F = 0
def check(name, ok, detail=""):
    global P, F; P += ok; F += not ok; print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))
src = open(HATS).read(); tree = ast.parse(src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BasePhysicalHAT")
want = {"mmiLoaderRunning", "statusFileStale", "indexingStep", "usbCheckText"}
body = [n for n in cls.body if (isinstance(n, ast.FunctionDef) and n.name in want) or
        (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("STATUS_STALE_SECS", "STATUS_CHECK_SECS", "_statusCheckedAt") for t in n.targets))]
d = tempfile.mkdtemp(); coms = os.path.join(d, "creating_menus.txt"); chk = os.path.join(d, "usbcheck.txt")
g = types.SimpleNamespace(a="")
ns = {"os": os, "time": time, "logging": logging, "globals": g, "comsFileName": coms, "usbCheckFileName": chk, "subprocess": subprocess}
K = type("H", (), {})
for n in body:
    exec(compile(ast.Module(body=[n], type_ignores=[]), HATS, "exec"), ns)
    if isinstance(n, ast.FunctionDef):
        fn = ns[n.name]; setattr(K, n.name, staticmethod(fn) if any(getattr(x, "id", "") == "staticmethod" for x in n.decorator_list) else fn)
    else:
        for t in n.targets: setattr(K, t.id, ns[t.id])
shown = []
disp = types.SimpleNamespace(showWaitPage=lambda t: shown.append(("wait", t)), showSuccessPage=lambda: shown.append(("success",)))
def hat(loader=False):
    h = K(); h.display = disp; h.indexPending = False; h.loaderRunning = lambda: loader; h.displayPowerOffTime = time.time() - 5; return h
def write(p, text, age=0):
    open(p, "w").write(text); t = time.time() - age; os.utime(p, (t, t))
def clear():
    for p in (coms, chk):
        if os.path.exists(p): os.remove(p)
check("usbCheckFileName defined in hats.py", 'usbCheckFileName = "/tmp/connectbox-usbcheck.txt"' in src)
clear(); write(chk, "Checking USB\nplease wait"); shown.clear(); h = hat()
r = h.indexingStep(False)
check("fresh check file: wait page with its text", shown == [("wait", "Checking USB\nplease wait")], shown)
check("... not counted as indexing (no checkmark later)", r is False)
check("... display kept on (power-off time moved on)", h.displayPowerOffTime > time.time() + 20, h.displayPowerOffTime - time.time())
os.remove(chk); shown.clear(); r = h.indexingStep(r)
check("check file gone, no indexing: no success page", shown == [] and r is False, shown)
clear(); write(chk, "Checking USB\nplease wait", age=60); shown.clear(); r = hat().indexingStep(False)
check("stale check file (60 s old): ignored", shown == [] and r is False, shown)
clear(); write(chk, "Checking USB\nplease wait"); write(coms, "Indexing 5%\nof 100 files"); shown.clear(); r = hat(loader=True).indexingStep(False)
check("indexing status wins over the check message", shown == [("wait", "Indexing 5%\nof 100 files")] and r is True, shown)
clear(); write(chk, "Checking USB\nplease wait"); shown.clear(); h = hat(); r = h.indexingStep(True)
check("check while an earlier index is still finishing: index state kept", r is True and shown == [("wait", "Checking USB\nplease wait")], (r, shown))
clear(); shown.clear(); r = hat().indexingStep(False); check("nothing to show: nothing shown", shown == [] and r is False)
print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
