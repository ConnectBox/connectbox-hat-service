# -*- coding: utf-8 -*-

"""
page_network.py - "IP addresses" status page (2026-11-11, Kirk).

Shows the IPv4 address of the box's three network interfaces, one per line:

    IP addresses
    AP   10.129.0.1
    WiFi 192.168.1.57
    Eth  not connected

AP is the access point the phones join, WiFi the client Wi-Fi interface (the
box's own connection to another network) and Eth the wired port.  The Wi-Fi
interface names come from /usr/local/connectbox/wificonf.txt, which PxUSBm
rewrites when the adapters change (wlan0 and wlan1 can swap at boot), so the
file is read again every time the page is drawn.  The wired port is eth0.

The client address changes at every boot (the MAC address is rotated on
purpose), so this page is where to read the address for SSH or the admin page.
"""

import os.path
import subprocess
from PIL import Image, ImageFont, ImageDraw

from .HAT_Utilities import get_device

WIFI_CONF = '/usr/local/connectbox/wificonf.txt'
ETH_IF = 'eth0'
NO_ADDRESS = 'not connected'
NO_INTERFACE = 'none'


def wifi_interfaces(path=None):
    """Return (access point interface, client interface) from wificonf.txt.

    The file holds "AccessPointIF=wlan1" and "ClientIF=wlan0" lines.  A name
    that is missing (file absent while PxUSBm rewrites it, or a box with one
    Wi-Fi adapter) is returned as ''.
    """
    names = {'AccessPointIF': '', 'ClientIF': ''}
    try:
        with open(path or WIFI_CONF, 'r', encoding='utf-8') as f:
            # One "key=value" per line; other lines (####END####) are ignored
            for line in f:
                key, sep, value = line.strip().partition('=')
                if sep and key in names:
                    names[key] = value.strip()
    except OSError:
        pass
    return names['AccessPointIF'], names['ClientIF']


def parse_address(ip_output, iface):
    """Return the interface's own IPv4 address from "ip -4 -o addr show" output, or ''.

    Each line reads "4: wlan1    inet 10.129.0.1/8 brd ... scope global wlan1".
    The last word is the address label: an alias such as "wlan1:0" (the
    captive portal's 172.217.3.174 on the access point) is not the interface's
    own address and is skipped.  The first own address is returned without
    its prefix length.
    """
    for line in ip_output.splitlines():
        # The part before "\" holds the address; the rest is lifetimes
        words = line.split('\\')[0].split()
        if len(words) < 4 or words[1] != iface or words[2] != 'inet':
            continue
        if words[-1] != iface:
            continue                    # labelled alias (iface:N)
        return words[3].split('/')[0]
    return ''


def address(iface):
    """Return what to show for one interface: its IPv4 address, NO_ADDRESS when
    it has none, or NO_INTERFACE when the box has no such interface (no name
    given, or the adapter is not there)."""
    if not iface or not os.path.exists('/sys/class/net/' + iface):
        return NO_INTERFACE
    try:
        out = subprocess.run(['ip', '-4', '-o', 'addr', 'show', 'dev', iface],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=5).stdout.decode('utf-8', 'replace')
    except (OSError, subprocess.SubprocessError):
        return NO_ADDRESS
    return parse_address(out, iface) or NO_ADDRESS


def rows():
    """Return the page's three lines, each a label padded to 5 characters and a
    value of at most 15 (an IPv4 address): 20 characters fit the 128-pixel
    display in the 6-pixel font."""
    ap, client = wifi_interfaces()
    return ["AP   " + address(ap),
            "WiFi " + address(client),
            "Eth  " + address(ETH_IF)]


class PageNetwork:
    """Status page listing the access point, client Wi-Fi and Ethernet addresses."""

    def __init__(self, device):
        """device: the luma display the page is drawn on."""
        self.device = device

    def draw_page(self):
        """Draw the title and the three address lines (read afresh each time)."""
        dir_path = os.path.dirname(os.path.abspath(__file__))
        title_font = ImageFont.load(dir_path + '/assets/HaxM-12.pil')
        # HaxM-10 is 6 pixels a character: label + longest address (20
        #  characters, 120 pixels) fits the 128-pixel display on one line
        row_font = ImageFont.load(dir_path + '/assets/HaxM-10.pil')
        size = (self.device.width, self.device.height)
        img = Image.new('RGBA', size, (255, 255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((2, 1), "IP addresses", font=title_font, fill="black")
        # Three rows under the title, 15 pixels apart
        for i, text in enumerate(rows()):
            d.text((2, 19 + 15 * i), text, font=row_font, fill="black")
        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageNetwork(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
