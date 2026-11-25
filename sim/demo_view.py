#!/usr/bin/env python3
"""Prints the flight log the firmware wrote to the (peer) SST25 flash, decoded: state and sensor/estimator fields every 500 ms.
usage: demo_view.py out/flash.bin"""
import sys
from decode_flash import decode, STATES

_, _, _, cols, rows = decode(open(sys.argv[1], "rb").read())
ix = {c: i for i, c in enumerate(cols)}
rows = [[STATES[r[0]]] + r[1:] for r in rows]
print("firmware flight log (SST25 flash), every 500 ms of log time")
last = -1
for r in rows:
    t = r[ix["t_ms"]]
    if t // 500 != last:
        last = t // 500
        print(f"{r[ix['state']]:<13} t={t / 1000:5.1f} s  baro_alt {r[ix['baro_alt']]:7.1f} m  pres {r[ix['baro_pres']] / 100:7.1f} hPa  "
              f"|v| {r[ix['velo_mag']]:6.1f} m/s  ax {r[ix['ax']]:6.1f} m/s2")
states = {r[ix["state"]] for r in rows}
print(f"done: {len(rows)} frames logged by the firmware, states seen: {', '.join(s for s in ('LAUNCH_DETECT', 'ASCENT', 'APOGEE', 'DESCENT') if s in states)}")
