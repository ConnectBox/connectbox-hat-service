# -*- coding: utf-8 -*-
"""
===========================================
  HAT_Utilities.py
  https://github.com/Connectbox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  GeoDirk - May 2018
===========================================
"""
import logging
from luma.core import cmdline, error  # pylint: disable=import-error


def GetReleaseVersion():
    """Read the release version"""
    try:
        with open("/etc/connectbox-release", 'r') as release:
            return str(release.read())
    except OSError:
        logging.warning("Error reading release version")
    return "unknown"


def get_device(actual_args=None):
    """
    Create device from command-line arguments and return it.
    """
    device_type = "NEO"
    port = 0    #We assume its a NEO which is port 0
    parser = cmdline.create_parser(description='luma.examples arguments')
    with open("/proc/cpuinfo", encoding = 'utf8')as f:
        filx = f.read()
        if ("Raspberry" in filx):
            if ("Compute Module" in filx):
                port = 0
                device_type = "CM"
            else:           #all other Raspberry Pi version other than compute modules
                port = 1
                device_type = "PI"
    f.close()
    # for NEO we use i2c-port 0. For Pi's other than compute modules we use i2c-port 1
    
    args = parser.parse_args(['--i2c-port', str(port)])

    if args.config:
        # load config from file
        config = cmdline.load_config(args.config)
        args = parser.parse_args(config + actual_args)

    # create device
    try:
        device = cmdline.create_device(args)
    except error.Error as e:
        parser.error(e)

    return device


def display_settings(args):
    """
    Display a short summary of the settings.
    :rtype: str
    """
    iface = ''
    display_types = cmdline.get_display_types()
    if args.display not in display_types['emulator']:
        iface = 'Interface: {}\n'.format(args.interface)

    return 'Display: {}\n{}Dimensions: {} x {}\n{}'.format(
        args.display, iface, args.width, args.height, '-' * 40)
