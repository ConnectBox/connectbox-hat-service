"""Fix 75: a failed power-off must not freeze the front panel.  usage: python3 shutdown_test.py <hats.py>

shutdownDevice() used to call os.system(poweroff) and then loop for ever, whatever happened; on a
64-bit box the 32-bit poweroff binary could not run and the panel froze on the powering-off screen.
Runs BasePhysicalHAT.shutdownDevice / _runShutdownCommand / _shutdownFailed with fake GPIO and display
and real little scripts as the shutdown commands.
"""
import ast, logging, os, sys, tempfile, threading, time, types, subprocess
HATS = sys.argv[1]; P = F = 0
def check(name, ok, detail=""):
    global P, F; P += ok; F += not ok; print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))
src = open(HATS).read(); tree = ast.parse(src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BasePhysicalHAT")
want = {"shutdownDevice", "_runShutdownCommand", "_shutdownFailed"}
body = [n for n in cls.body if (isinstance(n, ast.FunctionDef) and n.name in want) or isinstance(n, ast.Assign)]
check("shutdownDevice and its helpers are in BasePhysicalHAT",
      want <= {n.name for n in body if isinstance(n, ast.FunctionDef)}, sorted(n.name for n in body if isinstance(n, ast.FunctionDef)))
gpio = types.SimpleNamespace(HIGH=1, LOW=0, output=lambda pin, v: None)
ns = {"os": os, "time": time, "logging": logging, "subprocess": subprocess, "GPIO": gpio, "sys": sys}
K = type("H", (), {})
for n in body:
    try:
        exec(compile(ast.Module(body=[n], type_ignores=[]), HATS, "exec"), ns)
    except Exception:
        continue
    if isinstance(n, ast.FunctionDef):
        setattr(K, n.name, ns[n.name])
    else:
        for t in n.targets:
            if hasattr(t, "id") and t.id in ns: setattr(K, t.id, ns[t.id])
d = tempfile.mkdtemp()
def script(name, body):
    p = os.path.join(d, name); open(p, "w").write("#!/bin/sh\n" + body + "\n"); os.chmod(p, 0o755); return p
marker = os.path.join(d, "ran")
ok_cmd = script("ok", "echo $0 >> " + marker + "; exit 0")
fail_cmd = script("fail", "echo $0 >> " + marker + "; echo boom >&2; exit 3")
missing = os.path.join(d, "no-such-poweroff")
armhf = os.path.join(d, "armhf-like"); open(armhf, "wb").write(b"\x7fELF\x01\x01\x01" + b"\0" * 200); os.chmod(armhf, 0o755)
def hat(poweroff, fallback, wait=1):
    h = K(); events = []
    h.display = types.SimpleNamespace(showPoweringOff=lambda: events.append("poweringoff"),
                                      showErrorPage=lambda t: events.append(("error", t)))
    h.solidLED = lambda: events.append("led"); h.displayPowerOffTime = 0; h.PIN_LED = 6
    h.POWEROFF_COMMAND = [poweroff]; h.FALLBACK_SHUTDOWN_COMMAND = [fallback]
    h.SHUTDOWN_WAIT_SECS = wait; h.SHUTDOWN_COMMAND_TIMEOUT_SECS = 5
    return h, events
def run(h, limit=10):
    """Run shutdownDevice in a thread; True if it returned within limit seconds (no freeze)."""
    if os.path.exists(marker): os.remove(marker)
    t = threading.Thread(target=h.shutdownDevice, daemon=True); t0 = time.time(); t.start(); t.join(limit)
    return not t.is_alive(), time.time() - t0
def ran():
    return [os.path.basename(l.strip()) for l in open(marker)] if os.path.exists(marker) else []

check("no busy 'while True: pass' left in shutdownDevice",
      "while True:\n            pass" not in src.split("def shutdownDevice")[1].split("def ")[0])
h, ev = hat(missing, fail_cmd); done, secs = run(h)
check("poweroff missing, fallback fails: returns (panel not frozen)", done, secs)
check("... error page 'Shutdown failed' shown and LED put back", ("error", "Shutdown failed") in ev and ev[-1] == "led", ev)
check("... display kept on for a while", h.displayPowerOffTime > time.time() + 30, h.displayPowerOffTime - time.time())
check("... fallback was tried", ran() == ["fail"], ran())
h, ev = hat(armhf, ok_cmd, wait=1); done, secs = run(h)
check("poweroff cannot run (wrong-architecture binary): fallback shutdown started", ran() == ["ok"], ran())
check("... waits SHUTDOWN_WAIT_SECS for the system to go down, then reports", done and secs >= 1, secs)
check("... still running after the wait: error page, LED back", ("error", "Shutdown failed") in ev and ev[-1] == "led", ev)
h, ev = hat(ok_cmd, fail_cmd, wait=2); done, secs = run(h)
check("poweroff works: fallback not run", ran() == ["ok"], ran())
check("... powering-off screen first, kept while waiting", ev[:1] == ["poweringoff"] and secs >= 2, (ev, secs))
h, ev = hat(fail_cmd, fail_cmd); done, secs = run(h)
check("both commands fail (exit 3): returns with error page", done and ("error", "Shutdown failed") in ev and ran() == ["fail", "fail"], (done, ev, ran()))
h, ev = hat(ok_cmd, ok_cmd, wait=60); done, secs = run(h, limit=3)
check("shutdown started: does not return early (screen stays)", not done, secs)
print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
