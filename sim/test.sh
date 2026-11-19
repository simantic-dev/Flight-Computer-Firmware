#!/bin/sh
# Runs the committed Rev 2 flight image (sim/fw/appa.elf, STM32H750 app on the H743 stand-in) against the Python
# sensor/flash/LoRa peers, replaying sim/data/locked_in_flight.csv open loop for 9 s of virtual time, LoRa telemetry
# off (labelled fallback, see sim/README.md "LoRa stall"). Pass = fc_state_update walks IDLE -> CALIB ->
# LAUNCH_DETECT -> ASCENT -> APOGEE -> DESCENT and the flash log holds decoded ASCENT and DESCENT frames.
# Not run here: the full 196 s / 4442-frame flight of the README (about 100 s wall).
cd "$(dirname "$0")/.." || exit 1
OUT=$(mktemp -d) || exit 1
trap 'rm -rf "$OUT"' EXIT
export SDR_LAUNCH_S=6 SDR_LORA=0 SDR_FLASH=$OUT/flash.bin
${SIM:-sim} run --scenario sim/scenario.yaml --timeout 9 --trace-symbol fc_state_update > "$OUT/o.txt" 2> "$OUT/e.txt"
rc=$?
python3 sim/decode_flash.py "$OUT/flash.bin" > "$OUT/frames.csv" 2>"$OUT/d.txt"
fail=0
chk() { # name pattern file
  if grep -qF -- "$2" "$3"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi
}
[ $rc -eq 0 ] && echo "ok   sim exit 0" || { echo "FAIL sim exit $rc"; fail=1; }
chk "IDLE"          "r0=0x00000001" "$OUT/o.txt"
chk "CALIB"         "r0=0x00000002" "$OUT/o.txt"
chk "LAUNCH_DETECT" "r0=0x00000003" "$OUT/o.txt"
chk "ASCENT"        "r0=0x00000004" "$OUT/o.txt"
chk "APOGEE"        "r0=0x00000006" "$OUT/o.txt"
chk "DESCENT"       "r0=0x00000007" "$OUT/o.txt"
chk "flash log has ASCENT frames"  "ASCENT," "$OUT/frames.csv"
chk "flash log has DESCENT frames" "DESCENT," "$OUT/frames.csv"
if grep -qiE "HardFault|panic|fail_fast|Guru" "$OUT/o.txt" "$OUT/e.txt"; then
  echo "FAIL fault line seen"; fail=1
else echo "ok   no fault lines"; fi
exit $fail
