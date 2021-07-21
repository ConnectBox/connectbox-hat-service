# ConnectBox HAT services

Python3 service to work with the ConnectBox project's HAT. The program will detect if you have the 100 Unit Run HAT (H1Y2018) or the OLED HAT (H2Y2018).  If the 100 Unit Run HAT, it will perform voltage monitoring and shutdown the device when a low-battery state is reached. If the OLED, then it will perform voltage monitoring like the H1Y2018 HAT and display various messages onto the OLED display.

To develop or run:

0. Start with a ConnectBox image > 20180526 (which installs the required system libraries and tools)
1. Clone the repo `git clone https://github.com/kirkdwilson/connectbox-hat-service
2. cd into the repo
3. run `pip install -e .`  (to create an editable python installation and install required python libraries)
4. run the service manually with `neo_batterylevelshutdown` (if the service is already running courtesy of the ConnectBox image, you will need to stop it first with `systemctl stop neo-battery-shutdown.service`

As this is an editable python installation, code changes made in the repository will be applied directly, without any reinstallation or changes to PYTHONPATH

If you are deploying on a 256MB NEO, you will need to run `MAX_CONCURRENCY=1 pip install -e .` because the default installation method for the pillow library will exhaust the memory on the device.
