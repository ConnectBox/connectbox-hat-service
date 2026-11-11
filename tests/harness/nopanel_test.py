"""Hat service on a Raspberry Pi with no ConnectBox front panel (2026-11-11).

usage: python3 nopanel_test.py <hats.py> <cli.py> <displays.py>

Before the fix the service crash-looped on a plain Pi board, and on a CM whose front-panel bus was stuck:
- getHATClass() returned q1y2018HAT when the AXP209 did not answer; that class (made only for the NEO)
  has no Raspberry Pi set-up and raised "no attribute 'displayPowerOffTime'";
- DummyHAT (no OLED) has no LED pin, and BasePhysicalHAT.__init__ -> solidLED() raised AttributeError;
- DummyDisplay had no showWaitPage/showSuccessPage, so indexing on a box without an OLED raised too.
Now a Pi/CM without an AXP209 runs DummyHAT, the LED helpers do nothing without an LED pin, any other
DummyDisplay call does nothing, and on a Pi/CM DummyHAT exits (for a systemd restart) when the AXP209
answers again.  Functions are taken from the files with ast and run with fake GPIO / AXP209 / globals.
"""
import ast, logging, sys, time, types
HATS, CLI, DISP = sys.argv[1:4]; P = F = 0
def check(name, ok, detail=""):
    global P, F; P += bool(ok); F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))

def node(path, kind, name, inside=None):
    tree = ast.parse(open(path, encoding="utf-8").read())
    body = tree.body
    if inside:
        body = next(n for n in body if isinstance(n, ast.ClassDef) and n.name == inside).body
    return next(n for n in body if isinstance(n, kind) and n.name == name)

def run(n, ns, path):
    exec(compile(ast.Module(body=[n], type_ignores=[]), path, "exec"), ns)

# ---- 1. LED helpers without an LED pin -------------------------------------------------
calls = []
gpio = types.SimpleNamespace(HIGH=1, LOW=0, output=lambda pin, v: calls.append((pin, v)))
ns = {"GPIO": gpio, "time": types.SimpleNamespace(sleep=lambda s: None)}
for m in ("solidLED", "blinkLED"):
    run(node(HATS, ast.FunctionDef, m, "BasePhysicalHAT"), ns, HATS)
K = type("K", (), {"solidLED": ns["solidLED"], "blinkLED": ns["blinkLED"], "check_AP_up": lambda self: 1})
k = K()
try:
    k.solidLED(); k.blinkLED(2); ok, err = True, ""
except Exception as e:
    ok, err = False, repr(e)
check("no LED pin (DummyHAT): solidLED/blinkLED do nothing and do not raise", ok and calls == [], (err, calls))
k.PIN_LED = 6; k.solidLED()
check("with an LED pin: solidLED still drives it (LOW = on when the AP is up)", calls == [(6, 0)], calls)

# ---- 2. getHATClass: no AXP209 ---------------------------------------------------------
fn = node(CLI, ast.FunctionDef, "getHATClass")
class NoAxp:
    def __init__(self, port): raise OSError(121, "Remote I/O error")
hats = types.SimpleNamespace(DummyHAT="DummyHAT", q1y2018HAT="q1y2018HAT", q3y2018HAT="q3y2018HAT",
                             q4y2018HAT="q4y2018HAT", q3y2021HAT="q3y2021HAT")
for dev, want in [("PI", "DummyHAT"), ("CM", "DummyHAT"), ("NEO", "q1y2018HAT")]:
    g = types.SimpleNamespace(device_type=dev, port=10 if dev == "CM" else (1 if dev == "PI" else 0))
    ns = {"logging": logging, "globals": g, "hats": hats, "GPIO": gpio,
          "utilities": types.SimpleNamespace(get_device=lambda: object()),
          "axp209": types.SimpleNamespace(AXP209=NoAxp)}
    run(fn, ns, CLI)
    try:
        got = ns["getHATClass"]()
    except Exception as e:
        got = repr(e)
    check(f"OLED found, no AXP209, device {dev}: {want}", got == want, got)
ns["utilities"] = types.SimpleNamespace(get_device=lambda: (_ for _ in ()).throw(OSError("no OLED")))
run(fn, ns, CLI)
check("no OLED at all: DummyHAT (unchanged)", ns["getHATClass"]() == "DummyHAT")

# ---- 3. DummyHAT main loop: looks for the front panel again on a Pi/CM -------------------
cls = node(HATS, ast.ClassDef, "DummyHAT")
class Stop(Exception): pass
def dummy_hat(dev, axp_answers_after):
    tries = {"n": 0}
    class FakeAxp:
        def __init__(self, port):
            tries["n"] += 1
            if tries["n"] <= axp_answers_after: raise OSError(121, "Remote I/O error")
        def close(self): pass
    steps = {"n": 0}
    class Base:
        def indexingStep(self, v):
            steps["n"] += 1
            if steps["n"] > 20: raise Stop()
            return False
    g = types.SimpleNamespace(device_type=dev, port=10)
    ns = {"BasePhysicalHAT": Base, "globals": g, "logging": logging, "AXP209": FakeAxp, "sys": sys,
          "time": types.SimpleNamespace(time=time.time, sleep=lambda s: None), "setup_GPIO": lambda: None}
    run(cls, ns, HATS)
    D = ns["DummyHAT"]; D.PANEL_RECHECK_SECS = 0
    h = D.__new__(D)
    try:
        h.mainLoop(); return "returned", tries["n"]
    except SystemExit as e:
        return ("exit", e.code), tries["n"]
    except Stop:
        return "kept running", tries["n"]
r, n = dummy_hat("CM", axp_answers_after=2)
check("CM, AXP209 back after 2 failed checks: exits non-zero for a systemd restart",
      r[0] == "exit" and r[1] not in (0, None) and n == 3, (r, n))
r, n = dummy_hat("PI", axp_answers_after=10**6)
check("plain Pi, no front panel: keeps running (no exit)", r == "kept running" and n > 0, (r, n))
r, n = dummy_hat("NEO", axp_answers_after=0)
check("NEO: no re-check (unchanged behaviour)", r == "kept running" and n == 0, (r, n))

# ---- 4. DummyDisplay: any display call is a no-op ---------------------------------------
ns = {}
run(node(DISP, ast.ClassDef, "DummyDisplay"), ns, DISP)
d = ns["DummyDisplay"](None)
try:
    d.showWaitPage("Indexing 4%"); d.showSuccessPage(); d.showErrorPage("x"); d.showPoweringOff()
    d.moveForward(); ok, err = True, ""
except Exception as e:
    ok, err = False, repr(e)
check("DummyDisplay: wait/success/error/powering-off pages do nothing, no error", ok, err)
check("DummyDisplay: display_type still 'DummyDisplay'", d.display_type == "DummyDisplay")
try:
    getattr(d, "__deepcopy__"); dunder = "returned"
except AttributeError:
    dunder = "AttributeError"
check("DummyDisplay: special (__x__) names are not faked", dunder == "AttributeError", dunder)

print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
