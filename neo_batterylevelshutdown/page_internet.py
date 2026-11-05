# -*- coding: utf-8 -*-

"""
page_internet.py - "Internet shared" status page (2026-11-05).

Shows whether internet sharing is on (admin page Advanced switch, brand.j2
"internet_sharing") and how much data phones passed through it: the running
total PxUSBm keeps in /usr/local/connectbox/internet_usage.json (bytes, down =
internet to phones, up = phones to internet; Reset on the admin page).
The page is in the status pages only while sharing is on or the total is not
zero (wanted(), checked whenever the page changes).
"""

import json
import os.path
from PIL import Image, ImageFont, ImageDraw

from .HAT_Utilities import get_device

BRAND_FILE = '/usr/local/connectbox/brand.j2'
USAGE_FILE = '/usr/local/connectbox/internet_usage.json'


def sharing_on():
    """brand.j2 internet_sharing (key matched without regard to case) is 1."""
    try:
        with open(BRAND_FILE, 'r', encoding='utf-8') as f:
            brand = json.load(f)
        for k, v in brand.items():
            if k.lower() == 'internet_sharing':
                return str(v).strip().lower() in ('1', 'true')
    except (OSError, ValueError, AttributeError):
        pass
    return False


def usage():
    """(down, up) bytes shared so far, (0, 0) if unknown."""
    try:
        with open(USAGE_FILE, 'r', encoding='utf-8') as f:
            u = json.load(f)
        return max(0, int(u.get('down', 0))), max(0, int(u.get('up', 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0, 0


def wanted():
    """Show the page: sharing is on, or something has been counted."""
    down, up = usage()
    return sharing_on() or (down + up) > 0


def human(n):
    """Bytes in decimal units (1 MB = 1,000,000 bytes), as on the admin page."""
    if n >= 1e9:
        return "%.2f GB" % (n / 1e9)
    if n >= 1e6:
        return "%.1f MB" % (n / 1e6)
    if n >= 1e3:
        return "%.1f kB" % (n / 1e3)
    return "%d B" % n


class PageInternet:
    def __init__(self, device):
        self.device = device

    def draw_page(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        font = ImageFont.load(dir_path + '/assets/HaxM-12.pil')
        size = (self.device.width, self.device.height)
        img = Image.new('RGBA', size, (255, 255, 255, 255))
        d = ImageDraw.Draw(img)
        down, up = usage()
        d.text((2, 1), "Internet: %s" % ("ON" if sharing_on() else "off"), font=font, fill="black")
        d.text((2, 17), "Total %s" % human(down + up), font=font, fill="black")
        d.text((2, 33), "Down  %s" % human(down), font=font, fill="black")
        d.text((2, 49), "Up    %s" % human(up), font=font, fill="black")
        self.device.display(img.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageInternet(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
