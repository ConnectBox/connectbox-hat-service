
import logging
import smbus2
from . import globals
import time


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

def init_ATTiny_Talking():
    """Mark the ATTiny88 co-processor as reachable so voltage reads are attempted.

    Called once during CM4 HAT init.  If communication later fails, check_ATTiny()
    sets ATTiny_Talking = False to suppress further i2c attempts and hide the
    multi-battery display page.
    """
    global ATTiny_Talking
    ATTiny_Talking = True

# -------------------------------------------------------------------------
# Low-level i2c read/write helpers.
# smbus2 context-manager (__enter__/__exit__) is not supported on all
# kernel versions, so the bus is opened and closed manually.  Both helpers
# retry up to 9 times before giving up and return -1 on failure so callers
# can detect communication loss without catching exceptions themselves.
# -------------------------------------------------------------------------

def i2c_read(reg, device=ATTINY_ADDRESS):
    """Read one byte from an i2c register, retrying up to 9 times on error.

    Parameters
    ----------
    reg    : int  — register address to read
    device : int  — i2c device address (default: ATTiny88 at 0x14)

    Returns
    -------
    int — register value (0-255) on success, -1 on 9 successive failures.
    """
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
    """Write one byte to an i2c register, then read back to confirm, retrying up to 9 times.

    Parameters
    ----------
    reg    : int  — register address to write
    val    : int  — byte value to write
    device : int  — i2c device address (default: ATTiny88 at 0x14)

    Returns
    -------
    int — value read back after write on success, -1 on 9 successive failures.
    """
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
    """Placeholder — not implemented."""
    p = 9

def v_update_array(bat_voltage):    # array voltages lsb = 1mV
    """Update the shared voltage_array with the current battery's voltage from the AXP209.

    The ATTiny88 (register 0x31) tells us which battery slot is currently in use.
    Register 0x33 is a bitmap of batteries wired in a welded (parallel) group —
    all slots in that group are set to the same voltage.  Register 0x32 is a bitmap
    of physically present batteries; absent slots are zeroed so the average ignores them.

    Parameters
    ----------
    bat_voltage : int — current battery voltage in mV as read from the AXP209.
    """
    global ATTiny_Talking
    if ATTiny_Talking == True:
        bat_number = i2c_read(0x31)
        welded =  i2c_read(0x33)                    # batGroup bitmap (zero based)
        b_present = i2c_read(0x32)

    else:
        bat_number = 1      # defaults if we can't talk to the ATTiny 
        welded = 0x0F 
        b_present = 0x0F
        # perhaps block out the multi-bat page if we can't talk to ATTiny ??

    voltage_array[0] = bat_number
    # store voltage (lsb = 1 mV) directly to local array
    voltage_array[bat_number] = bat_voltage     # bat_number is 1 based

    if ((1 << (bat_number -1)) & welded) > 0:   # current battery part of welded group
        for n in range(4):                      # set all voltages in welded group to current bat voltage
            if ((1<<n)&welded) > 0:
                voltage_array[n+1] = bat_voltage  # lsb = 1mV
    for n in range(4):                      # set all voltages for batteries not present to 0
        if ((1<<n)&b_present) == 0:
            voltage_array[n+1] = 0  


def get_in_use():
    """Return the welded-group bitmap from ATTiny register 0x33.

    The bitmap indicates which battery slots are wired together in a welded
    (parallel) group and therefore share voltage.  Falls back to 0xF (all four
    slots in use) when ATTiny communication has failed so callers see a safe default.

    Returns
    -------
    int — 4-bit bitmap where bit N set means battery slot N+1 is in the welded group.
    """
    global ATTiny_Talking
    if ATTiny_Talking == True:
        in_use_map = i2c_read(0x33)
    else:
        in_use_map = 0xF
    return in_use_map

# -------------------------------------------------------------------------
# ATTiny health check.
# Register 0x51 is a free-running counter that increments every ~300 ms.
# Reading it twice with a 300 ms gap and comparing lets us detect whether the
# ATTiny is alive (counter changes) or stuck / absent (counter frozen).
# Called once per Axp209HAT main loop iteration so the state is stable within
# each loop cycle.
# -------------------------------------------------------------------------
def check_ATTiny():
    """Test ATTiny i2c communication and disable multi-battery display if it fails.

    Reads the free-running counter at register 0x51 twice, 300 ms apart.
    If both reads return the same value the ATTiny is frozen (or i2c is broken),
    so ATTiny_Talking is set to False and the multi-battery screen is hidden.
    """
    global ATTiny_Talking
    if ATTiny_Talking == True:
        try:
            result1 = i2c_read(0x51)
            time.sleep(0.3)
            result2 = i2c_read(0x51)
            if result1 == result2:
                ATTiny_Talking = False          # ATTiny giving stuck answer (i2c working... just not useful)
                globals.screen_enable[3]=0      # turn off multi batt screen if ATTiny communication fails
        except:                                 # if here, i2c to ATTiny has failed
            ATTiny_Talking = False
            globals.screen_enable[3]=0      # turn off multi batt screen if ATTiny communication fails
            logging.error("ERROR: ATTiny i2c failed)")

def reset_ATTiny():
    """Trigger a battery-register reset cycle on the ATTiny (register 0x40).

    Called once at CM4 HAT init to cycle through all battery slots so the AXP209
    can read their voltages before the first display update.
    """
    global ATTiny_Talking
    if ATTiny_Talking == True:
        logging.info("Resetting battery registers (i2c_read(0x40))")
        result1 = i2c_read(0x40)


# -------------------------------------------------------------------------
# Battery voltage accessors.
# voltage_array is the central store updated by v_update_array() each main-loop
# iteration.  Index 0 holds the currently active battery slot number (1-based);
# indices 1-4 hold the voltage (mV) of batteries 1-4 respectively.
# -------------------------------------------------------------------------
voltage_array = [0,0,0,0,0]

def bat_voltage(x):
    """Return the stored voltage (mV) for battery slot x (1-4), or slot count from index 0."""
    return voltage_array[x]

def bat_number():
    """Return the currently active battery slot number as reported by the ATTiny (1-4)."""
    return voltage_array[0]

# Function not used... also... the math is wrong (lsb is 16mV not 1mV)
def bat_fuel(x):
    """Estimate state-of-charge percentage for battery slot x.  NOTE: currently unused."""
    if x >0 and x<5:
        fuel = (voltage_array[x] - 3275)/7.67
        if fuel <= 5:
            return 5
        return fuel

def averageBat():
    """Return the mean voltage (mV) across all battery slots that report > 0 V.

    Slots reporting 0 mV are treated as absent and excluded from the average.
    Returns 0 if no batteries have been read yet (startup state).
    """
    batV = 0
    count = 0
    for reg in range (1,5):
        value = bat_voltage(reg)
        batV += value
        if (value > 0):
           count = count + 1
    if count == 0:
        return 0    # handle startup prior to any batteries being read
    batV = batV / count
    batV = round(batV, 0)
    return(batV)

def averageFuel():
    """Return estimated average state-of-charge (%) across all present battery slots.

    Uses the linear approximation Fuel = (Vavg_mV - 3275) / 7.67 which maps the
    usable voltage range ~3.275 V (0 %) to ~4.04 V (100 %).  Clamped to [5, 100].
    """
    avg_voltage = averageBat()
    fuel = (avg_voltage - 3275)/7.67
    if fuel <= 5:
        fuel = 5
    if fuel > 99:
        fuel = 100
    return(fuel)



