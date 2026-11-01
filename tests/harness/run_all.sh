#!/bin/bash
# Runs the front-panel harnesses (fixes 21-51) against this checkout.
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
[ $FAILED = 0 ] && echo "ALL PASSED" || echo "SOME TESTS FAILED"; exit $FAILED
