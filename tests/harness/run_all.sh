#!/bin/bash
# Runs the front-panel harnesses (fixes 21-51, 75, 79) against this checkout.
# usage: bash tests/harness/run_all.sh [connectbox-pi checkout]     (default: ../connectbox-pi beside this repo)
# The build installs this repo's neo_batterylevelshutdown package and then copies connectbox-pi's
# displays.py and page_display_image.py over it, so the tests run on that same "deployed" set.
HERE=$(dirname "$(realpath "$0")"); HAT=$(realpath "$HERE/../.."); PI=$(realpath "${1:-$HAT/../connectbox-pi}")
OV=$PI/ansible/roles/hat-service/files/neo-batterylevelshutdown
[ -f "$OV/displays.py" ] || { echo "connectbox-pi not found at $PI (give its path)"; exit 2; }
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
cp -r "$HAT/neo_batterylevelshutdown/." "$D/"; cp "$OV/displays.py" "$OV/page_display_image.py" "$D/"
FAILED=0
run() { local name=$1; shift; echo "== $name"; if python3 "$@" > "$D/out.txt" 2>&1; then grep -v "^[[:space:]]*$" "$D/out.txt" | tail -n 1; else cat "$D/out.txt"; FAILED=1; fi
        grep -q "FAIL\]\|\[FAIL\|^FAIL" "$D/out.txt" && FAILED=1; }
run "sim43 (buttons, admin commands, pages)" "$HERE/sim43.py" "$D"
run "unit35c (brand.j2 read/write, status file)" "$HERE/unit35c.py" "$D"
run "usb_test (usb.py)"                       "$HERE/usb_test.py" "$D/usb.py"
run "fscheck_test (usb.py file-system check)" "$HERE/fscheck_test.py" "$D/usb.py"
run "movemount_test (usb.py moveMount)"       "$HERE/movemount_test.py" "$D/usb.py"
run "test51_hats (Checking USB on the panel)" "$HERE/test51_hats.py" "$D/hats.py"
run "shutdown_test (failed power-off does not freeze the panel)" "$HERE/shutdown_test.py" "$D/hats.py"
run "nopanel_test (Raspberry Pi without a front panel)" "$HERE/nopanel_test.py" "$D/hats.py" "$D/cli.py" "$D/displays.py"
run "network_page_test (IP addresses page)" "$HERE/network_page_test.py" "$D/page_network.py" "$D/displays.py" "$D/globals.py"
run "internet_switch_test (Internet page admin switch)" "$HERE/internet_switch_test.py" "$D/displays.py" "$D/globals.py"
run "webcmd_test (copy commands from the admin page)" "$HERE/webcmd_test.py" "$D/buttons.py"
[ $FAILED = 0 ] && echo "ALL PASSED" || echo "SOME TESTS FAILED"; exit $FAILED
