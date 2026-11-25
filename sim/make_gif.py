"""Builds results/flight.gif from the run's two outputs: out/frames.csv (the flight log the firmware wrote to the
simulated flash, decoded by decode_flash.py) and out/trace.log (--trace-symbol fc_state_update). Pillow + ffmpeg only.
usage: python3 make_gif.py out/frames.csv out/trace.log results/flight.gif <sim-version>     (run from sim/)"""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gifkit import *

CSV, TRACE, OUT, VER = sys.argv[1:5]
F0 = 4.0637   # virtual time of the first logged frame (the last calibration sample, trace.log / README)
rows = list(csv.DictReader(l for l in open(CSV) if not l.startswith("#")))
T = [F0 + float(r["t_ms"]) / 1000 for r in rows]
alt0 = float(rows[0]["baro_alt"])
ALT = [(t, float(r["baro_alt"]) - alt0) for t, r in zip(T, rows)]
VEL = [(t, float(r["velo_mag"])) for t, r in zip(T, rows)]
ACC = [(t, float(r["ax"])) for t, r in zip(T, rows)]
PRES = [(t, float(r["baro_pres"]) / 100) for t, r in zip(T, rows)]
NAMES = ["", "IDLE", "CALIB", "LAUNCH_DETECT", "ASCENT", "COAST", "APOGEE", "DESCENT"]   # r0 of fc_state_update
tr = []
for l in open(TRACE):
    m = re.match(r"\[([\d.]+)s\] \(TRACE\) fc_state_update .* r0=0x(\w+)", l)
    if m: tr.append((float(m[1]), int(m[2], 16)))
st_t = {n: next((t for t, s in tr if s == n), None) for n in range(1, 8)}
STATES = NAMES[1:]
COLS = [BLUE, BLUE, AMBER, GREEN, GREEN, AMBER, RED]
con = [(t, "INFO", f"fc_state_update(new state = {s} {NAMES[s]})") for t, s in tr]

def last(series, t):
    r = [v for a, v in series if a <= t]
    return r[-1] if r else None

def marks(c, x, y, w, h, t):
    for n, tt in st_t.items():
        if tt is not None and tt <= t and n >= 3:
            px = x + 60 + (w - 80) * tt / 15.0
            c.d.line((px, y + 34, px, y + h - 22), fill=COLS[n - 1], width=2)
            c.text(px + 4, y + 36 + [3, 4, 6, 7].index(n) * 15, NAMES[n], 13, COLS[n - 1], True)

def draw(c, t):
    c.header("Sun Devil Rocketry flight computer: flight-state machine", "Rev 2 flight firmware on a simulated STM32H7, sensors replayed from the team's locked_in_flight.csv. Readouts are what the firmware logged to its flash.", t)
    c.panel(24, 84, 1232, 96, "Flight state (fc_state_update): when each state was entered")
    act = max([n for n, tt in st_t.items() if tt is not None and tt <= t], default=None)
    c.chain(40, 112, 1200, 58, STATES, None if act is None else act - 1, [st_t[n] if st_t[n] is not None and st_t[n] <= t else None for n in range(1, 8)], COLS, 16)
    bx = 40 + 4 * (1200 - 60) / 7 + 4 * 10   # COAST box: never entered in this run
    c.d.rectangle((bx + 4, 150, bx + 160, 164), fill=PANEL)
    c.text(bx + (1200 - 60) / 14, 157, "never entered", 14, DIM, False, True, "mm")
    a, v, ax, p = last(ALT, t), last(VEL, t), last(ACC, t), last(PRES, t)
    tw = 296
    c.tile(24, 192, tw, 88, "ALTITUDE ABOVE PAD (BARO)", f"{a:.0f}" if a is not None else "--", "m", CYAN)
    c.tile(24 + (tw + 16), 192, tw, 88, "VELOCITY (FIRMWARE NAV)", f"{v:.0f}" if v is not None else "--", "m/s", GREEN)
    c.tile(24 + 2 * (tw + 16), 192, tw, 88, "ACCEL X", f"{ax:.1f}" if ax is not None else "--", "m/s^2", AMBER)
    c.tile(24 + 3 * (tw + 16), 192, tw, 88, "BARO PRESSURE", f"{p:.1f}" if p is not None else "--", "hPa", VIOLET)
    c.strip(24, 292, 606, 200, ALT, t, 15.0, 0, 1500, "altitude above pad, m (logged to flash)", CYAN, "m")
    marks(c, 24, 292, 606, 200, t)
    c.strip(650, 292, 606, 200, VEL, t, 15.0, 0, 300, "velocity, m/s (firmware nav estimate)", GREEN, "m/s")
    marks(c, 650, 292, 606, 200, t)
    c.log(24, 504, 1232, 140, con, t, "firmware trace: --trace-symbol fc_state_update (state passed to the state machine)", 14)
    c.text(24, 652, "APOGEE is flagged at CSV t=1.9 s while the replayed flight is still climbing (open-loop replay, cause not investigated: see sim/README.md). Log fills at 4442 frames.", 14, AMBER)
    c.footer(VER, SPEED)

SPEED = 1.0
n = render(draw, 15.0, SPEED, OUT)
print("frames", n)
