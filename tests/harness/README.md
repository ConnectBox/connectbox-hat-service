# Front-panel test harnesses

Tests written for the October–November 2026 fixes (21–51). Hardware (GPIO, OLED, mounts) is faked;
files are real, in temporary folders. Each harness takes the file or folder under test as its argument,
so the same test can be run on old code to show it fails there.

## Run them all

```
bash tests/harness/run_all.sh [path to connectbox-pi]     # default: ../connectbox-pi beside this repo
```

Linux, Python 3. The build installs this repo's `neo_batterylevelshutdown` package and then copies
connectbox-pi's `ansible/roles/hat-service/files/neo-batterylevelshutdown/displays.py` and
`page_display_image.py` over it. `run_all.sh` builds that same "deployed" set in a temporary folder and
tests it; testing this repo's files alone fails (for example `displays.page_enabled` is only in the
connectbox-pi copy).

## The harnesses

| File | Covers | Run by hand |
|---|---|---|
| `sim43.py` | admin commands (copy from/to USB, erase, space check), error pages that stay lit, key held after a failed copy, progress %, one checkmark, button timing | `python3 sim43.py <deployed folder>` |
| `unit35c.py` | brand.j2 atomic write/read, no dosfsck on a mounted key, one success page, status file | `python3 unit35c.py <deployed folder>` |
| `usb_test.py` | `usb.isUsbPresent()`: /dev/sdX1 and whole-disk keys | `python3 usb_test.py <usb.py>` |
| `fscheck_test.py` | `usb._check_file_system` by type (FAT exit 1, NTFS, exFAT); never on a mounted key | `python3 fscheck_test.py <usb.py>` |
| `movemount_test.py` | `usb.moveMount` to /media/usb11 per file system | `python3 movemount_test.py <usb.py>` |
| `test51_hats.py` | the panel shows PxUSBm's "Checking USB" | `python3 test51_hats.py <hats.py>` |

Results on 2026-11-01 (hat-service 731a6ff + connectbox-pi fc7d58c): 84, 23, 10, 8, 4 and 9 passed, none failed.

`tests/test_neo_batterylevelshutdown.py` is the older unit-test suite of this repo.
See connectbox-pi `docs/testing.md` for all tests and when to run them.
