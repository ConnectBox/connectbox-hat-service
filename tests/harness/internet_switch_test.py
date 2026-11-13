"""Admin switch for the front panel's Internet data page (brand.j2 lcd_pages_internet, 2026-11-13).

usage: python3 internet_switch_test.py <displays.py> <globals.py>

displays.internetPageWanted() puts the internet page in the page list only while
the page is wanted (internet sharing on or data counted) AND the admin switch is on:
- switch 1 / "1" / missing (older globals.py or brand.j2): shown exactly when wanted;
- switch 0 / "0" / "false": never shown, even while wanted;
- other pages' screen_enable entries are left alone.
globals.py must read the switch with a default of on, apart from the screen_enable
list, so an older brand.j2 without the key keeps the page.
The method is taken from displays.py and run with fake globals and pages; no display
or program is used.
"""
import re, sys, textwrap, types
DISPLAYS, GLOBALS = sys.argv[1], sys.argv[2]
P = F = 0


def check(name, ok, detail=""):
    """Count and print one check."""
    global P, F
    P += bool(ok); F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))


# -- take internetPageWanted() out of displays.py and make it a plain function -------
d = open(DISPLAYS, encoding="utf-8").read()
m = re.search(r"\n(    def internetPageWanted\(self\):\n.*?)(?=\n    def )", d, re.S)
check("displays.py has internetPageWanted()", m is not None)
src = textwrap.dedent(m.group(1))


class PageInternet:
    """Stand-in for page_internet.PageInternet (the isinstance check needs a class)."""


class Other:
    """Stand-in for any other status page."""


def run(switch, wanted, missing=False):
    """Run internetPageWanted() with the given switch value and wanted() result;
    returns the resulting screen_enable list (pages: other, internet, other)."""
    g = types.SimpleNamespace(screen_enable=[1, 0, 1])
    if not missing:
        g.lcd_pages_internet = switch
    pi = types.SimpleNamespace(PageInternet=PageInternet, wanted=lambda: wanted)
    ns = {"globals": g, "page_internet": pi, "logging": types.SimpleNamespace(debug=lambda *a: None)}
    exec(src, ns)
    self = types.SimpleNamespace(statusPages=[Other(), PageInternet(), Other()])
    ns["internetPageWanted"](self)
    return g.screen_enable


check("switch 1, wanted: shown", run(1, True) == [1, 1, 1], run(1, True))
check("switch 1, not wanted: hidden", run(1, False) == [1, 0, 1], run(1, False))
check("switch \"1\" (text), wanted: shown", run("1", True) == [1, 1, 1])
check("switch 0, wanted: hidden", run(0, True) == [1, 0, 1], run(0, True))
check("switch \"0\" (text), wanted: hidden", run("0", True) == [1, 0, 1])
check("switch \"false\", wanted: hidden", run("false", True) == [1, 0, 1])
check("no switch at all (older globals.py), wanted: shown", run(None, True, missing=True) == [1, 1, 1])
check("other pages' entries untouched when hidden", run(0, True)[0] == 1 and run(0, True)[2] == 1)

# -- globals.py reads the switch with a default of on ----------------------------------
g = open(GLOBALS, encoding="utf-8").read()
check("globals.py default lcd_pages_internet = 1", re.search(r"^lcd_pages_internet = 1$", g, re.M) is not None)
check("globals.init() declares it global", "global lcd_pages_internet" in g)
check("read with js.get(..., 1), outside the screen_enable try block",
      re.search(r"\n    lcd_pages_internet = js\.get\('lcd_pages_internet', 1\)\n", g) is not None)
print("\nResults: %d passed, %d failed" % (P, F)); sys.exit(1 if F else 0)
