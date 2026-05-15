"""
===========================================
  stats_page.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================

triggers the log refresh with:
sudo logrotate /etc/logrotate.hourly.conf
"""

import json
import os.path
import logging
import subprocess
from PIL import Image, ImageFont, ImageDraw
from .HAT_Utilities import get_device
import neo_batterylevelshutdown.globals as globals


def _fetch_topten():
    """Call 'connectboxmanage get topten' and parse the JSON response.

    Wraps the subprocess call and json.loads in a try/except so that a down
    port-5002 service (lms-api) or malformed output does not crash the display
    service.  Port 5002 can be unavailable after a restart until PM2 brings
    lms-api back up.

    Returns
    -------
    dict on success, None if the command fails or returns non-JSON output.
    """
    try:
        results = subprocess.run(
            ["connectboxmanage", "get", "topten"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        data = results.stdout.decode('utf-8').strip('\n')
        return json.loads(data)
    except Exception as e:
        logging.warning("topten fetch failed: %s", e)
        return None


class PageStats:
    def __init__(self, device, dt_range, page_num):
        """Initialise a stats display page.

        Parameters
        ----------
        device   : luma display device
        dt_range : str — time bucket ('hour', 'day', 'week', 'month', 'year')
        page_num : int — 1 for the first 5 results, 2 for results 6-10
        """
        self.device = device
        self.dt_range = dt_range
        self.page_num = page_num

    def readStatsJSON(self):
        """Fetch and print top-ten stats to stdout (debug helper, not called by draw_page)."""
        data = _fetch_topten()
        if data is None:
            print('topten unavailable')
            return
        print('============================')
        print('     ' + self.dt_range)
        print('============================')
        for p in data[self.dt_range]:
            print('file: ' + p['resource'])
            print('count: ' + str(p['count']))
        print('')

    # pylint: disable=too-many-locals, too-many-branches
    def draw_page(self):
        """Render the stats page onto the OLED display.

        Loads the appropriate background image for dt_range, overlays the top-ten
        content access counts retrieved from connectboxmanage, and pushes the
        composite to the display.  If the topten data is unavailable (port 5002
        down), the unhappy-face image is left visible and the method returns
        without crashing — ensuring the display service keeps running.
        """
        # -------------------------------------------------------------------------
        # Select the background image for this time range.
        # -------------------------------------------------------------------------
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/stats_h_page.png'
        if self.dt_range == 'hour':
            img_path = dir_path + '/assets/stats_h_page.png'
        elif self.dt_range == 'day':
            img_path = dir_path + '/assets/stats_d_page.png'
        elif self.dt_range == 'week':
            img_path = dir_path + '/assets/stats_w_page.png'
        elif self.dt_range == 'month':
            img_path = dir_path + '/assets/stats_m_page.png'
        elif self.dt_range == 'year':
            img_path = dir_path + '/assets/stats_y_page.png'
        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)

        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/CODE2000.TTF'
        font10 = ImageFont.truetype(font_path, 10)
        font20 = ImageFont.truetype(font_path, 13)
        d = ImageDraw.Draw(txt)

        # -------------------------------------------------------------------------
        # Fetch stats data; bail out gracefully if unavailable.
        # The unhappy-face in the background image signals to the user that data
        # is not ready yet — no additional error page is needed.
        # -------------------------------------------------------------------------
        data = _fetch_topten()
        if data is None:
            out = Image.alpha_composite(img, txt)
            self.device.display(out.convert(self.device.mode))
            self.device.show()
            return

        logging.info("connectbox manage results: "+str(data))
        y = 0
        count = 0

        # Label which page (1 or 2) of results is shown in the top-right corner.
        if self.page_num == 1:
            d.text((107, 22), 'p1', font=font20, fill="black")
        else:
            d.text((107, 22), 'p2', font=font20, fill="black")

        # -------------------------------------------------------------------------
        # If any result has a 'resource' key, cover the unhappy face with white so
        # the data rows are readable against the plain background.
        # -------------------------------------------------------------------------
        for p in data[self.dt_range]:
            if 'resource' in p.keys():
                d.rectangle((25, 1, 75, 128), fill="white")

        # -------------------------------------------------------------------------
        # Render up to 5 rows per page.  page_num==1 shows items 1-5; page_num==2
        # shows items 6-10.  Each row is 12px tall starting from y=0.
        # -------------------------------------------------------------------------
        for p in data[self.dt_range]:
            media = p['resource']
            if self.page_num == 1:
                d.text((2, y), '(%s) %s' %
                       (str(p['count']), media),
                       font=font10, fill="black")
                y += 12
                count += 1
                if count == 5:
                    break
            else:
                count += 1
                if count > 5:
                    d.text((2, y), '(%s) %s' %
                           (str(p['count']), media),
                           font=font10, fill="black")
                    y += 12
                    if count == 10:
                        break

        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()


if __name__ == "__main__":
    try:
        PageStats(get_device(), 'hour', 1).draw_page()
        # PageStats(get_device(), 'hour', 2).draw_page()
        # PageStats(get_device(), 'day', 1).draw_page()
        # PageStats(get_device(), 'day', 2).draw_page()
        # PageStats(get_device(), 'week', 1).draw_page()
        # PageStats(get_device(), 'week', 2).draw_page()
        # PageStats(get_device(), 'hour', 1).draw_page()
        # PageStats(get_device(), 'month', 2).draw_page()
    except KeyboardInterrupt:
        pass
