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
from PIL import Image, ImageFont, ImageDraw
from .HAT_Utilities import get_device
import neo_batterylevelshutdown.globals as globals


class PageStats:
    def __init__(self, device, dt_range, page_num):
        self.device = device
        self.dt_range = dt_range
        self.page_num = page_num

    def readStatsJSON(self):
        results = subprocess.run(["connectboxmanage", "get", "topten"], stdout=subprocess.PIPE)
        data = results.stdout.decode('utf-8').strip('\n')
        data = json.load(data)
        print('============================')
        print('     ' + self.dt_range)
        print('============================')
        for p in data[self.dt_range]:
            print('file: ' + p['resource'])
            print('count: ' + str(p['count']))
        print('')

    # pylint: disable=too-many-locals, too-many-branches
    def draw_page(self):
        # get an image
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
        font_path = dir_path + '/assets/HaxM-10.pil'
        font10 = ImageFont.load(font_path)
        font_path = dir_path + '/assets/HaxM-13.pil'
        font20 = ImageFont.load(font_path)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        # draw text, full opacity
        results = subprocess.run(["connectboxmanage", "get", "topten"], stdout=subprocess.PIPE)
        data = results.stdout.decode('utf-8').strip('\n')
        data = json.load(data)
        y = 0
        count = 0

        if self.page_num == 1:
            d.text((107, 22), 'p1', font=font20, fill="black")
        else:
            d.text((107, 22), 'p2', font=font20, fill="black")

        # check to see if we have data or not
        for p in data[self.dt_range]:
            if 'resource' in p.keys():
                # cover up the unhappy face
                d.rectangle((25, 1, 75, 128), fill="white")

        for p in data[self.dt_range]:
            media = p['resource']
            if self.page_num == 1:
                # trim out directories
                d.text((2, y), '(%s) %s' %
                       (str(p['count']), media),
                       font=font10, fill="black")
                y += 12
                count += 1
                if count == 5:
                    break
            else:
                # trim out directories
                count += 1
                if count > 5:
                    d.text((2, y), '(%s) %s' %
                           (str(p['count']), media),
                           font=font10, fill="black")
                    y += 12

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
