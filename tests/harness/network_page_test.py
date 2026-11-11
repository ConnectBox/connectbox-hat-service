"""IP addresses page (page_network.py, 2026-11-11): which address is shown per interface.

usage: python3 network_page_test.py <page_network.py> <displays.py> <globals.py>

- wificonf.txt: access point and client interface names (either order, file
  missing, one adapter only);
- "ip -4 -o addr show" output: the interface's own address, not the captive
  portal alias (wlan1:0), not another interface's, none when it has no address;
- the three rows: label + value fit 20 characters (6-pixel font, 128-pixel display);
- the page is in the status pages just before the internet page, and
  globals.screen_enable has one entry per status page.
No display, network or program is used (PIL and the display helper are faked).
"""
import importlib.util, os, re, sys, tempfile, types
PAGE, DISPLAYS, GLOBALS = sys.argv[1], sys.argv[2], sys.argv[3]
P = F = 0


def check(name, ok, detail=""):
    global P, F
    P += bool(ok); F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))


# Fake the package, PIL and the display helper so the page file loads anywhere
pkg = types.ModuleType("nbs"); pkg.__path__ = []; sys.modules["nbs"] = pkg
hu = types.ModuleType("nbs.HAT_Utilities"); hu.get_device = lambda: None; sys.modules["nbs.HAT_Utilities"] = hu
if "PIL" not in sys.modules:
    try:
        import PIL  # noqa
    except ImportError:
        pil = types.ModuleType("PIL"); pil.Image = pil.ImageFont = pil.ImageDraw = types.SimpleNamespace(); sys.modules["PIL"] = pil
spec = importlib.util.spec_from_file_location("nbs.page_network", PAGE)
pn = importlib.util.module_from_spec(spec); spec.loader.exec_module(pn)

# -- wificonf.txt ------------------------------------------------------------------
T = tempfile.mkdtemp(); conf = os.path.join(T, "wificonf.txt")
open(conf, "w").write("AccessPointIF=wlan1\nClientIF=wlan0\n####END####\n")
check("wificonf: access point wlan1, client wlan0", pn.wifi_interfaces(conf) == ("wlan1", "wlan0"), pn.wifi_interfaces(conf))
open(conf, "w").write("ClientIF=wlan1\nAccessPointIF=wlan0\n")
check("wificonf: lines in the other order", pn.wifi_interfaces(conf) == ("wlan0", "wlan1"))
open(conf, "w").write("AccessPointIF=wlan0\nClientIF=\n####END####\n")
check("wificonf: one adapter, no client interface", pn.wifi_interfaces(conf) == ("wlan0", ""))
check("wificonf missing: no names, no error", pn.wifi_interfaces(os.path.join(T, "gone.txt")) == ("", ""))

# -- addresses (output as on the CM5 test box) --------------------------------------
IP = ("1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever\n"
      "2: eth0    inet 192.168.1.31/24 brd 192.168.1.255 scope global dynamic eth0\\       valid_lft 7125sec preferred_lft 7125sec\n"
      "4: wlan1    inet 172.217.3.174/24 scope global wlan1:0\\       valid_lft forever preferred_lft forever\n"
      "4: wlan1    inet 10.129.0.1/8 brd 10.255.255.255 scope global noprefixroute wlan1\\       valid_lft forever preferred_lft forever\n")
check("access point: its own address, not the captive portal alias wlan1:0", pn.parse_address(IP, "wlan1") == "10.129.0.1", pn.parse_address(IP, "wlan1"))
check("ethernet address without the prefix length", pn.parse_address(IP, "eth0") == "192.168.1.31")
check("interface with no address: empty", pn.parse_address(IP, "wlan0") == "")
check("a name that another name starts with is not matched (wlan1 vs wlan10)", pn.parse_address(IP.replace("wlan1", "wlan10"), "wlan1") == "")
check("empty output: empty", pn.parse_address("", "eth0") == "")

# -- the three rows -----------------------------------------------------------------
pn.wifi_interfaces = lambda path=None: ("wlan1", "wlan0")
pn.address = lambda iface: {"wlan1": "10.129.0.1", "wlan0": pn.NO_ADDRESS, "eth0": "192.168.100.100"}[iface]
r = pn.rows()
check("rows: AP, WiFi, Eth in that order", r == ["AP   10.129.0.1", "WiFi not connected", "Eth  192.168.100.100"], r)
check("rows fit 20 characters, also with the longest address", all(len(x) <= 20 for x in r) and len("WiFi " + "255.255.255.255") <= 20, r)
spec = importlib.util.spec_from_file_location("nbs.page_network2", PAGE)
pn2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(pn2)
check("no interface name: 'none'; interface not on the box: 'none'", pn2.address("") == pn2.NO_INTERFACE and pn2.address("nosuchif9") == pn2.NO_INTERFACE)

# -- underlined title (also used by the internet page) ----------------------------------
class FakeDraw:
    def __init__(self): self.calls = []
    def text(self, xy, text, **k): self.calls.append(("text", xy, text))
    def line(self, xy, **k): self.calls.append(("line", xy))
class FakeFont:                         # 8 pixels a character, 14 high, like HaxM-12
    def getbbox(self, text): return (0, 0, 8 * len(text), 14)
fd = FakeDraw(); pn2.draw_title(fd, "IP addresses", FakeFont())
check("title: text at (2,1), then a line under it as wide as the text (y 15, x 2..97)",
      fd.calls == [("text", (2, 1), "IP addresses"), ("line", (2, 15, 97, 15))], fd.calls)
class OldFont:                          # Pillow before 8.0: getsize only
    def getsize(self, text): return (8 * len(text), 14)
fd = FakeDraw(); pn2.draw_title(fd, "Internet: ON", OldFont())
check("title: same line with an old Pillow font (getsize)", fd.calls[1] == ("line", (2, 15, 97, 15)), fd.calls)
internet = open(os.path.join(os.path.dirname(PAGE), "page_internet.py"), encoding="utf-8").read()
check("internet page draws its title with draw_title", "from .page_network import draw_title" in internet and 'draw_title(d, "Internet: %s"' in internet)

# -- page list and screen_enable -------------------------------------------------------
d = open(DISPLAYS, encoding="utf-8").read(); g = open(GLOBALS, encoding="utf-8").read()
pages = re.search(r"self\.statusPages = \[(.*?)\n        \]", d, re.S).group(1)
names = re.findall(r"^\s+(page_\w+)\.", pages, re.M)
check("displays.py imports page_network", "from . import page_network" in d)
check("IP addresses page is just before the internet page, admin page last",
      names.index("page_network") + 1 == names.index("page_internet") and names[-1] == "page_display_image", names)
default = re.search(r"^screen_enable = \[([^\]]*)\]", g, re.M).group(1).split(",")
check("globals.screen_enable default has one entry per status page", len(default) == len(names), (len(default), len(names)))
check("default: IP addresses page on, internet page off", default[names.index("page_network")].strip() == "1" and default[names.index("page_internet")].strip() == "0", default)
brand = re.search(r"screen_enable = \[\n(.*?)\n        \]", g, re.S).group(1)
entries = [l for l in brand.split("\n") if l.strip() and not l.strip().startswith("#")]
check("screen_enable from brand.j2 has one entry per status page", len(entries) == len(names), (len(entries), len(names)))
check("lcd_pages_network is read with a default (older brand.j2 lacks it)", "js.get('lcd_pages_network', 1)" in entries[names.index("page_network")], entries[names.index("page_network")])
print("\nResults: %d passed, %d failed" % (P, F)); sys.exit(1 if F else 0)
