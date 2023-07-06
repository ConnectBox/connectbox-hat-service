# -*- coding: utf-8 -*-

"""Console script for neo_batterylevelshutdown."""

# Modified 11/05/19 JRA to detect no battery unit by asking the AXP209 whether battery exists
# AXP209 code comes from github.com/artizirk/python-axp209

import sys
import logging
import axp209
import time
import click
import os
import RPi.GPIO as GPIO  # pylint: disable=import-error
import neo_batterylevelshutdown.globals as globals
import neo_batterylevelshutdown.hats as hats
import neo_batterylevelshutdown.displays as displays
import neo_batterylevelshutdown.HAT_Utilities as utilities

# Global definitions for this module
hatClass = 0
progress_file = "/usr/local/connectbox/expand_progress.txt"


def getHATClass():
    logging.debug("Entering get Hat Class")
    # We assume the HAT is not present if we're unable to setup the pin
    #  or read from it. That's the safe option and means that we won't
    #  immediately shutdown devices that don't have a HAT if we've incorrect
    #  detected the presence of a HAT

    try:
        # See if we can find an OLED
        utilities.get_device()
    except OSError:
        # No OLED. Treat it as a DummyHAT
        logging.debug("No OLED detected, We are retuning a Dummy HAT")
        return hats.DummyHAT

# Express all pin numbers in BCM nomenclature for compatibility with CM4
#  (which requires BCM)
# We will carry the original, NEO based names but use BCM pin numbers
#  Note that PA1 is used only for version testing in NEO, so for RPi (PI and CM4)
#   versions we specify an un-connected pin... GPIO25
#   PA0 only used on HAT7 for OTG sense... spec un-connected pin on others
    if globals.device_type == "NEO":
        PA6 = 12    #PA6    Amber LED pin #
        PA1 = 22    #PA1    Test for HAT 4.6.7 (all other HATs have this pin unconnected) pin #
        PG11 = 7    #PG11   Test of HAT 7 pin #
        PA0 = 11    #PA0    OTG sense (HAT7), not used on others pin #
    if globals.device_type == "CM":
        PA6 = 6     #GPIO6/30
        PA1 = 25    #GPIO25/41
        PG11 = 4    #GPIO4/54   Actually GPIO4 is PB2 which will be HIGH on CM4 HAT
        PA0 = 17    #GPIO17/50
    if globals.device_type == "PI":
        PA6 = 18    #device is Pi GPIO18
        PA1 = 23    #GPIO25
        PG11 = 4    #GPIO4
        PA0 = 17    #GPIO17

    GPIO.setup(PA6,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PG11,GPIO.IN, pull_up_down=GPIO.PUD_UP)
    if GPIO.input(PA6) == GPIO.LOW:
        logging.debug("NEO HAT not detected")
        return hats.DummyHAT
    logging.debug("passed GPIO no hat test looking for AXP209")
    try:
        axp = axp209.AXP209(globals.port)
    # moved the battexists = axp.battery_exists test to the individual battery display pages
        axp.close()
        # AXP209 found... we have HAT from Q3Y2018 or later
        # Test PA1...
        #    HIGH => Q3Y2018 == HAT 4.6.7
        #    LOW =>          == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; HAT 7; CM4
        # Test PG11...
        #    HIGH => Q4Y2018 == HAT 5.0.0; 5.1.1 (with or w/o battery); HAT 6; CM4
        #    LOW  => Q3Y2021 == HAT 7

        GPIO.setup(PA1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        if GPIO.input(PA1) == GPIO.LOW:
            if (GPIO.input(PG11) == GPIO.HIGH):
            # This would include CM4 HAT as "PG11" is assigned to GPIO4
            #  and that is wired to PB2 (normally HIGH)
                logging.info("Q4Y2018 HAT Detected")
                return hats.q4y2018HAT
            else:
                logging.info("Q3Y2021 HAT Detected")
                return hats.q3y2021HAT
        else:
        # PA1 is HIGH, so this is HAT 4.6.7
            logging.info("Q3Y2018 HAT Detected")
            return hats.q3y2018HAT

    except OSError:
        # There is no AXP209 on the Q12018 HAT
        #  so this is either a real Q1Y2018 HAT or we have a bare processor
        logging.info("Q1Y2018 HAT Detected")
        return hats.q1y2018HAT
    except KeyboardInterrupt:
        pass

    return hats.DummyHAT

def call_battery():
    page_battery.PageBattery(self.display_device, self.axp)
    return

# the OLED is already set from the hat class test.  No need to retest.

def getDisplayClass(hatClass):
    logging.debug("Entering get Display Class")
    if hatClass != hats.DummyHAT and hatClass !=0:
        return displays.OLED
    else:
        logging.info("No OLED detected")
        return displays.DummyDisplay




def fixfiles(a, c):
# This function is called to fix the files and restart the network daemons (if neeeded) based on what we have loaded.  
#  AP represents the Wlan that will serve as the Access point (passed in variable "a").  
#  CI is the ethernet interface which may or may not be there (passed in variable "c")
#  (Note: the values of a and c are numbers only.)

#  At the end of this function, wificonf.txt is written and reflects the settings in ALL required files
#   so if it is correct is wificonfig.txt, the supporting files are correct.

    logging.debug("Entering fix files")

    at = ""
    ct = ["","",""]
    try:
        f = open("/usr/local/connectbox/wificonf.txt", 'r')
        at = f.read()
        ct = at.split("\n")
        f.close()
    except:
        pass
    logging.info("wificonf.txt holds "+ct[0]+" and "+ct[1]+" for detected paramaters (AP, Client) "+a+" and "+c)
    
    if ("AccessPointIF=wlan"+ a) == ct[0] and (("ClientIF=wlan"+ c == ct[1] and c!="") | (c == "" and ct[1] == "ClientIF=")):
        logging.info("Skipped file reconfiguration as the configuration is the same")
        os.system("ifup wlan"+a)   # restart wlan ... other restarts needed??n
        return(0)           # we return because everything is the same and no need to reset netowrk settings.

    res = os.system("systemctl stop networking.service")
    res = os.system("systemctl stop hostapd")
    res = os.system("systemctl stop dnsmasq")
    res = os.system("systemctl stop dhcpcd")

# we only come here if we need to adjust the network settings
# Lets start with the /etc/network/interface folder
    f = open('/etc/network/interfaces.j2','r', encoding='utf-8')
    g = open('/etc/network/interfaces.tmp','w', encoding='utf-8')
    x = 0
    skip_rest = 0
    l = ""
    n = ""
    for y,l in enumerate(f):
        if skip_rest == 0:
            if '#CLIENTIF#' in l:       # #CLIENTIF# signals the end of AP and start of CI section
                x = 1                   #  signals we are in the ClientInterface section
            if 'wlan' in l:
                m = l.split('wlan')
                while (len(m)>1):

                    if x == 0:              # processing AP directives (this number is 0 until the CLIENTIF word is seen)
                         m[0] = m[0]+'wlan'+a                     #insert the AP wlan
#                    logging.debug("on interface line were setting $1: "+n)
                    else:                   # We are processing Client Interface directives
                        if c=="":
                            m[0] = '#'+m[0]+'wlan'+str(int(a)+1)
                        else:
                            if "#" == m[0][0]:
                                while m[0][1]=="#":             #take out any extra comment lines
# ?? colon in the next statement??
                                    m[0]=m[0][1:]
                                if len(m[0])<30:
# ?? colon in the next statement??                                    
                                    m[0] = m[0][1:]             #if the line is not a real command line but a comment then take out the # in front ssince we have C
                        m[0] = m[0]+'wlan'+c

                    while m[1][0].isnumeric():
# ?? colon in next line??
                        m[1] = m[1][1:]                        #Remove numeric characters
                    z=1
                    m[0]=m[0]+m[1]
                    while z < (len(m)-1):
                        m[z]=m[z+1]
                        z += 1
                    m.pop()
                n = str(m[0])
            else:                           # all lines of the enumerate of interfaces.j2 which DON'T contain 'wlan'
                if x>0:                     # we are done with AccessPoint directives... on to Client Interface directives
                    if c == "":
                        skip_rest=1         #if we hit here and have no client ie: c="" then we skip the rest fo the file
                    if l != "\n" and c =="":
                        l = "#" + l            # if for some reason we don't have a #ClIENTIF# reverence theen we comment out all of the client if c=""   
                n = str(l)
            g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("we have finished the temp /etc/network/interfaces.tmp file")
# Now we are done with the /etc/netowrk/interface  file
# Lets work on the dnsmask.conf file

    f = open('/etc/dnsmasq.conf','r', encoding='utf-8')
    g = open('/etc/dnsmasq.tmp','w', encoding='utf-8')
    x = 0
    l = ""
    n = ""
    for y,l in enumerate(f):
        if 'interface=wlan' in l:
             m = l.split('interface=wlan')
             n = str(m[0]+'interface=wlan'+a)
#             logging.debug("on dnsmasq were setting $1: "+n)
             x += 1
             while m[1][0].isnumeric():
                   m[1] = m[1][1:]
             n = str(n + m[1])
        else:
             n = str(l)
        g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/dnsmasq.tmp file")
# Now we are done with the /etc/dnsmasq.conf file
# lets move onto the hostapd.conf file

    f = open('/etc/hostapd/hostapd.conf','r', encoding='utf-8')
    g = open('/etc/hostapd/hostapd.tmp','w', encoding='utf-8')
    x = 0
    n = ""
    for y,l in enumerate(f):
        if 'interface=wlan' in l:
             m = l.split('interface=wlan')
             n = str(m[0]+'interface=wlan'+a)
#             logging.debug("on hostapd were setting $1: "+n)
             x += 1
             while m[1][0].isnumeric():
                   m[1] = m[1][1:]
             n = str(n + m[1])
        else:
             n = str(l)
        g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/hostapd/hostapd.tmp file")

# Nowe we need to exclude the AP from Wpa_supplicant control

    f = open('/etc/dhcpcd.conf','r', encoding='utf-8')
    g = open('/etc/dhcpcd.tmp','w', encoding='utf-8')
    x = 0
    n = ""
    for y,l in enumerate(f):
        if 'wlan' in l:
            if 'denyinterfaces' in l:
                 m = l.split('denyinterfaces wlan')
                 if c=="":
                    n = str(m[0] + "\n")
                 else:
                    n = str(m[0]+"denyinterfaces wlan" + c + "\n")
#             logging.debug("on dhcpcd.conf were setting $1: "+n)
                 x += 1
            else:
                 m = l.split('interface wlan')
                 n = str(m[0]+'interface wlan' + a + "\n" )
                 x += 1
        else:
             n = str(l)
        g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/dhcpcd.tmp file")

#  Now lets make sure we write out the configuration for future
#  (wificonf.txt reflects contents of all files which might need changes)
    try:
        f = open("/usr/local/connectbox/wificonf.txt", 'w')
        f.write("AccessPointIF=wlan"+ a +"\n")
        if c=="":
            f.write("ClientIF="+"\n")
        else:
            f.write("ClientIF=wlan"+ c +"\n")
        f.write("####END####\n")
        f.flush()
        f.close()
    except:
        pass

    os.system("sync")                                #we will ensure we clear all files and pending write data

# Now we are done with the network/interface.tmp, dnsmasq.tmp and hostapd.tmp file creations time to put them into action.

    if a != "":
         logging.info("taking interface down wlan"+a)
         os.system("ifdown wlan"+a)

    if c != "":
         logging.info("taking interface down wlan"+c)
         os.system("ifdown wlan"+c)
    time.sleep(10)

#    logging.info("We have taken the interfaces down now")
    os.system("mv /etc/network/interfaces /etc/network/interfaces.bak")
    os.system("mv /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.bak")
    os.system("mv /etc/dnsmasq.conf /etc/dnsmasq.bak")
    os.system("mv /etc/dhcpcd.conf /etc/dhcpcd.bak")

    os.system("cp /etc/hostapd/hostapd.tmp /etc/hostapd/hostapd.conf")
    os.system("cp /etc/dnsmasq.tmp /etc/dnsmasq.conf")
    os.system("cp /etc/network/interfaces.tmp /etc/network/interfaces")
    os.system("cp /etc/dhcpcd.tmp /etc/dhcpcd.conf")

    os.system("systemctl daemon-reload")             #we reload all the daemons since we changed the config.
    logging.info("We have completed the file copy copleteions")
    logging.info("we will reboot to setup the new interfaces")
    return(1)	# we want to reboot after this since we need to reload all the kernel drivers


def getNetworkClass():
    # this module is designed to get the available interfaces and define which interface is the client facing one and which is the
    # network facing interface.  The client interface is the AP interface and is based on either RTL8812AU or RTL8812BU or RTL88192U  The
    # network facing interface will use the on board BMC wifi module as long as an AP module is present.  If no AP module is present it will become
    # the AP although this is not optimal.  But this is useful for modules such as the RaspberryPi Zero W.

    global progress_file
    netwk=[]
    res = ""
    a = ""
    b = ""
    logging.debug("starting the get network class tool of cli.py on the battery page")
    res = os.popen("lshw -c Network").read()
    i=3
    if "wlan" in res:
        r = res.split("wlan")
        while i > 1:
            if len(r) <= 1:
                a == ""
            else:
                a = r[1][0]
            if a != "":
                if r[1].find("driver="):
                    b = r[1].split("driver=")[1].split(" ")[0]             #Split out the driver from the configuration line
                    netwk.append([a,b])                                    #add the wlan# and driver to the list
                    logging.info("found wlan driver combo, wlan"+a+" driver: "+b)
                    a = ""
                    b = ""
                else:
                    b = "none"
            i = len(r)                                              #slice out the [0 and 1] sections of the split
            res = ""
            while i>1:
                r[len(r)-i] = r[len(r)-i+1]
                i -=1
            s = r.pop(len(r)-1)                                       #remove the last item in the list
            i = len(r)
    logging.info("We finished the wlan lookup and are now going to edit the files.")
    AP = ""                                                         #access point interface
    CI = ""                                                         #client interface
    rbt = 0                                                         #reboot set to no
    if len(netwk) == 1:                                             #only one wlan interface AP only
        a = netwk[0][0]
        b = netwk[0][1]
        logging.info("single interface wlan"+a+" with driver "+b)
        # now we need to update the files for a single AP and no client
        AP = a;

    elif len(netwk) > 1:                                            #multiple wlan's so both AP and client interfaces
        logging.info("wlan"+netwk[0][0]+" with driver "+netwk[0][1])
        logging.info("wlan"+netwk[1][0]+" with driver "+netwk[1][1])
            # we have an rtl driver on this first wlan
        if "rtl88" in netwk[0][1]:                                  #if we have an rtl on the first wlan we will use it for AP
            AP = netwk[0][0]
            CI = netwk[1][0]
            #regardless of what we have there since its RTL-X we will use it for AP since we have no others
        if "rtl88" in netwk[1][1]:                                  #if we have an rtl on the second wlan we will use it for AP
            AP = netwk[1][0]                                    #interface 2 has the rtl and will be AP
            CI = netwk[0][0]                                    #interface 1 is on board or other andd will be the client side for network

        logging.info("AP will be: wlan"+AP+" ethernet facing is: wlan"+CI)
        if len(netwk) >=3:
            logging.info("we have more interfaces so they must be manually managed") # if we have more than 2 interfaces then they must be manually managed. rbt = fixfiles(AP,CI) #Go for fixing all the file entries 
            return(1)

    else:                                                           # we don't have even 1 interface
        logging.info("We have no wlan interfaces we can't function this way, rebooting to try to find the device")
        return(1)

    res = os.popen("ip link show "+AP).read()
    x = res.find("permaddr:")
    if ( x > 0 ):
        addr = res[(x+9):(x+26)]
    else:
         x = res.find("link/ether")
         if (x > 0):
             addr = res[(x+11):(x+27)]
         else:
             addr = 0
    if (addr > 0):
    # now that we have the AP file lets setup the /etc/systemd/network/10-wlanX.link file
         d = "/etc/systemd/network/10-"+AP+".link"
         try:
             f = open(d,'r')
             f.close()
         except:
             f = open(d, "w")
             f.write("\n[Match]\nMACAddress="+dap+"\n[Link]\nName="+AP+"\nMACAddressPolicy=random\n")
             f.close()
             os.sync()
             res=os.popen("update-initramfs -u")
             os.sync()
    rbt = fixfiles(AP,CI)                                       #Go for fixing all the file entries

    f = open(progress_file, "w")
    f.write("rewrite_netfiles_done")
    f.close()
    os.sync()
    return(rbt)


@click.command()
@click.option('-v', '--verbose', is_flag=True, default=True)

def main(verbose):

    global hatClass
    global progress_file

    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
         logging.basicConfig(level=logging.DEBUG)

    if not os.path.exists("/usr/local/connectbox/wificonf.txt"):
        f = open("/usr/local/connectbox/wificonf.txt", "w")
        f.write("AccessPointIF=\n")
        f.write("ClientIF=\n")
        f.write("#####END######")
        f.close()
        logging.info("wrote temp wificonf.txt file out\g\g\g")

#Initialize the Global Variables

    while not ( os.path.exists( progress_file )):
      logging.info("waiting\g\g")
      time.sleep(5)	#we wait till we have a progress file
    time.sleep(2)	#make sure its filled 
    f = open(progress_file, "r")
    a = f.read()
    while  (a == "fdisk_done" or a =='resize_done'):
        f.close()
        time.sleep(10)
        f = open(progress_file, "r")
        a = f.read()
#  we wait because we need the disk resize to finishe
    f.close()
    print("into global inits")
# Use BCM pin numbering scheme for compatibility with CM4 and use Board compatability for NEO
    globals.init()
    if globals.device_type == "NEO":
         GPIO.setmode(GPIO.BOARD)
    elif globals.device_type == "OZ2":
         import orangepi.zero2
         GPIO.setmode(orangepi.zero2.BOARD)
    else:
         GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

# Go find the netowrk interfaces and seteup the wans
#    if getNetworkClass():        #sets up the AP and Client interfaces if it returns a 1 we need  to shutdown and start over
#        logging.info("getNetworkClass  asked for a reboot \g\g")
#        GPIO.cleanup()       # clean up GPIO on  reboot
#        os.sync()
#        time.sleep(2)
#        os.system("shutdown -r now")
#    else:
#      logging.debug("Finished netowrk class")
#     logging.info("Restart wlan0 and wlan1 interfaces")
#      os.system("ifconfig wlan0 up")
#      os.system("ifconfig wlan1 up")

#      logging.info("Finished display class")
#      logging.info("writing running to progress_file")
#    f = open(progress_file, "w")
#    f.write("running")
#   f.close()
#    os.sync()

    hatClass = getHATClass()
    displayClass =getDisplayClass(hatClass)

#    logging.debug("display Class is: "+str(displayClass))
#    logging.debug("finished display class starting main loop")
    try:
         hatClass(displayClass).mainLoop()
    except KeyboardInterrupt:
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit

   
if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
