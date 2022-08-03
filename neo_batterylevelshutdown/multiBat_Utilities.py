
import logging
import smbus2
from . import globals


# JRA - 011322
#  Development of interaction with ATTiny88 running CM4_BatControl_9 arduino code
#  Note that rev 9 of the ATTiny code removes reading of the battery voltages but rather
#   enables writing of registers 0x21 - 0x24 for battery voltages of batteries 1 - 4 respectively.
#   Usefule ATTiny registers:
#      0x30 = battery count
#      0x31 = current battery
#      0x21 - 0x24 = battery 1 through 4 voltages (8 bit, lsb = 16 mv) - must be written by this code


ATTINY_ADDRESS = 0x14
I2C_BUS_NR = 10

# Utilities for reading i2c devices ... default address is ATTINY

def i2c_read(reg, device=ATTINY_ADDRESS):
#    logging.debug("i2c_read() port = %i ",globals.port)    
#    logging.debug("i2c_read() reg = %i ",reg) 
#    with smbus2.SMBus(globals.port) as bus:  # gives "AttributeError: __enter__" 
    bus = smbus2.SMBus(globals.port)
    value = -1
    i = 1
    while (value == -1) and (i < 10):
        try:
            value = bus.read_byte_data(device, reg)
            bus.close()     # success... close the bus
            return (value)
        except:
            i += 1
    bus.close()      # failed... close the bus 
    return (-1)      # return -1 if we have 10 successive read failures      

def i2c_write(reg, val, device = ATTINY_ADDRESS):
#    with smbus2.SMBus(globals.port) as bus: # gives "AttributeError: __enter__" 
    bus = smbus2.SMBus(globals.port)
    value = -1
    i = 1
    while (i < 10):
        try:
            bus.write_byte_data(device, reg, val)
            value = bus.read_byte_data(device, reg)
            bus.close()     # success... close the bus
            return (value)
        except:
            i += 1
    bus.close()             # failed... close the bus        
    return (-1)      # return -1 if we have 10 successive read failures  

def test():
    p = 9    

def v_update_array(bat_number):
    voltage_array[0] = bat_number
    # sync ATTiny voltage array (0x21 - 0x24) with python voltage_array[]
    for n in range (0,4):
        voltage_array[n+1] = i2c_read(0x21 + n) 

def get_in_use():
    in_use_map = i2c_read(0x33)
    return in_use_map        




# Here is a collection of battery read utilities for use by pages requiring battery voltage
# (There may be a better place to put the battery voltage functions)

# Central storage for battery voltages (written by AXP209HAT class function main)
# We use index 0 position to store the number of the battery in use
# We use index 1 - 4 to store the voltage of batteries 1 - 4
voltage_array = [0,0,0,0,0]      

def bat_voltage(x):     # NOTE: returned lsb = 1mv
    return 16*voltage_array[x]

def bat_number():
    return voltage_array[0]

def bat_fuel(x):
    if x >0 and x<5:
        fuel = (voltage_array[x] - 3275)/7.67  
        if fuel <= 5:
            return 5
        return fuel      

def averageBat():
    batV = 0
    count = 0
    for reg in range (1,5):
         value = bat_voltage(reg)
         batV += value
         if (value > 0):
            count = count + 1
         if count == 0:
            return 0 	# handle startup prior to any batteries being read   
    batV = batV / count
    batV = round(batV, 0)
    return(batV)

def averageFuel():
    avg_voltage = averageBat()
    fuel = (avg_voltage - 3275)/7.67
    if fuel <= 5:
        fuel = 5
    if fuel > 99:
        fuel = 100    
    return(fuel)



