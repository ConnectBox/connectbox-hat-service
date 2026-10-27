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

## Admin commands and the status display (ConnectBox NEO HAT)

- **Copy from USB / Copy to USB / Erase** (`buttons.py`) stop the content loader and kiwix-serve to free the stick and restart kiwix-serve afterwards (if it is enabled). While copying, the display shows `Copying 45%` and the size; the percentage comes from a watcher thread that compares the destination's free space with its value when the copy started (every 3 s) and never shows 100% before the copy has returned.
- After a copy or erase that changes the box's content, the command hands over to the main loop (`hat.indexPending`), which shows the loader's progress and **one** success page when `connectbox-loader` has finished. The re-index is started by PxUSBm (the command clears `/tmp/.internal_indexed`); the command starts the loader itself only if that has not happened within 30 s. Button presses on a wait page are ignored.
- `/tmp/creating_menus.txt` is the status text written by mmiLoader (e.g. `Indexing 45%` / `of 778 files`); the display shows it as a wait page while it exists. A file that has not changed for 15 s while no `mmiLoader.py` is running is a leftover and is removed (`statusFileStale()`).
- `brand.j2` is read with `globals.read_brand()` (retries for ~2 s) and written with `globals.write_brand()` (temporary file + rename, keeping owner and mode), because the main loop re-reads it on every pass and crashed once on a half-written file.
- `dosfsck`/`ntfsfix` are never run on a mounted device.
- The systemd unit (installed by connectbox-pi) sets `PYTHONUNBUFFERED=1`, so `print()` output reaches the journal immediately.
