# Open-loop stimulus shared by the sensor peers: the team's own emulator/resources/locked_in_flight.csv
# (BSD-3, SunDevilRocketry/Flight-Computer-Firmware emulator submodule). Whether it is a recorded flight
# is UNVERIFIED. MODELED SIMPLIFICATION: the rocket does not react to anything the firmware does.
#
# The CSV has only ~0.7 s of pad rows before boost. Before LAUNCH_S the pad rows are cycled; from
# LAUNCH_S the CSV is played in real (virtual) time, so csv_time = sim_time - LAUNCH_S.
import bisect, csv, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "locked_in_flight.csv")
LAUNCH_S = float(os.environ.get("SDR_LAUNCH_S", "8.0"))   # sim time at which CSV time 0 plays
PAD_END_S = 0.6                                            # boost starts at csv t = 0.65 s (ax 45 m/s2), so the cycled pad rows end at 0.6 s

# Firmware compensation (driver/baro/baro.c load_cal_data) fed by the NVM bytes the baro peer serves.
T1, T2, T3 = 27000, 19000, -10
P1 = 32767  # int16; every other pressure coefficient is 0
PAR_T1, PAR_T2, PAR_T3 = T1 / 0.00390625, T2 / 1073741824.0, T3 / 281474976710656.0
PAR_P1, PAR_P2 = (P1 - 16384) / 1048576.0, (0 - 16384) / 536870912.0


def comp_temp(raw):
    d = raw - PAR_T1
    return d * PAR_T2 + d * d * PAR_T3


def comp_press(raw, t):
    return raw * (PAR_P1 + PAR_P2 * t)


def _bisect(f, target, lo=0.0, hi=16777215.0):
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def raw_temp(t_c):
    return _bisect(comp_temp, t_c)


def raw_press(p_pa, t_c):
    return _bisect(lambda r: comp_press(r, t_c), p_pa)


class Flight:
    def __init__(self):
        rows = list(csv.DictReader(open(CSV)))
        self.t = [float(r["time"]) for r in rows]
        keys = ["ax", "ay", "az", "gx", "gy", "gz", "baro_pres", "baro_temp"]
        self.col = {k: [float(r[k]) for r in rows] for k in keys}
        self.rt = [raw_temp(x) for x in self.col["baro_temp"]]
        self.rp = [raw_press(p, x) for p, x in zip(self.col["baro_pres"], self.col["baro_temp"])]
        self.pad = bisect.bisect_left(self.t, PAD_END_S)

    def csv_time(self, now_s):
        return now_s - LAUNCH_S

    def at(self, now_s, key):
        """Linear interpolation of a CSV column (or raw baro column rt/rp) at sim time now_s."""
        c = self.csv_time(now_s)
        col = self.col[key] if key in self.col else getattr(self, key)
        if c < 0:  # pad: cycle the pre-boost rows
            return col[int(-c / 0.041) % self.pad]
        i = bisect.bisect_right(self.t, c) - 1
        if i >= len(self.t) - 1:
            return col[-1]
        f = (c - self.t[i]) / (self.t[i + 1] - self.t[i])
        return col[i] + f * (col[i + 1] - col[i])


FLIGHT = Flight()
