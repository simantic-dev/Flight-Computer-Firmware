"""Plots from out/frames.csv (decode_flash.py) and the stimulus CSV. Usage: plot_flight.py frames.csv fc_state.log out_dir"""
import csv, re, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

frames, log, outd = sys.argv[1:4]
LAUNCH_S = float(os.environ.get("SDR_LAUNCH_S", "6"))
CSV = os.path.join(os.path.dirname(__file__), "..", "emulator", "resources", "locked_in_flight.csv")
rows = [r for r in csv.DictReader(l for l in open(frames) if not l.startswith("#"))]
f = lambda k: [float(r[k]) for r in rows]
truth = list(csv.DictReader(open(CSV)))
tt = [float(r["time"]) for r in truth]
NAMES = {1: "IDLE", 2: "CALIB", 3: "LAUNCH_DETECT", 4: "ASCENT", 5: "COAST", 6: "APOGEE", 7: "DESCENT", 8: "LANDED"}
tr = [(float(m.group(1)) - LAUNCH_S, NAMES[int(m.group(2), 16)]) for l in open(log)
      for m in [re.match(r"\[([\d.]+)s\] \(TRACE\) fc_state_update .* r0=(0x\w+)", l)] if m and int(m.group(2), 16) >= 3]
# frame t_ms=0 is launch_detect_start_time, set when the last calibration sample is taken (sim 4.064 s, the final
# sensor_dump before the flight loop), not when LAUNCH_DETECT is entered (3.53 s)
LD = float(os.environ.get("SDR_FRAME0_S", "4.064"))
t = [float(r["t_ms"]) / 1000 + LD - LAUNCH_S for r in rows]  # frame time is ms since LAUNCH_DETECT was entered
pa = lambda p: 44330 * (1 - (p / 101325) ** 0.1903)  # international standard atmosphere
p0 = float(truth[0]["baro_pres"])
fig, ax = plt.subplots(4, 1, figsize=(11, 11), sharex=True)
a0 = f("baro_alt")[0]
ax[0].plot(t, [x - a0 for x in f("baro_alt")], label=f"firmware baro_alt minus its pad value {a0:.0f} m (frame)")
ax[0].plot(tt, [pa(float(r["baro_pres"])) - pa(p0) for r in truth], "--", label="CSV pressure -> ISA altitude above pad")
ax[0].set_ylabel("altitude (m)")
ax[1].plot(t, f("ax"), label="firmware ax (frame)")
ax[1].plot(tt, [float(r["ax"]) for r in truth], "--", lw=.6, label="CSV ax")
ax[1].set_ylabel("accel X (m/s^2)")
ax[2].plot(t, f("baro_pres"), label="firmware baro_pres (frame)")
ax[2].plot(tt, [float(r["baro_pres"]) for r in truth], "--", label="CSV pressure")
ax[2].set_ylabel("pressure (Pa)")
ax[3].plot(t, f("velo_mag"), label="firmware velo_mag")
ax[3].set_ylabel("velocity (m/s)")
ax[3].set_xlabel("time since CSV t=0 (s)")
for a in ax:
    for x, n in tr:
        a.axvline(x, color="k", lw=.5, ls=":")
    a.legend(loc="upper right", fontsize=8)
    a.grid(alpha=.3)
for x, n in tr:
    ax[0].text(x, ax[0].get_ylim()[1], " " + n, rotation=90, va="top", fontsize=8)
ax[0].set_title("Rev 2 flight firmware in the sim, open-loop replay of locked_in_flight.csv")
fig.tight_layout()
fig.savefig(os.path.join(outd, "flight_full.png"), dpi=110)
ax[0].set_xlim(-3, t[-1] + 0.5)
fig.savefig(os.path.join(outd, "flight.png"), dpi=110)
fig, a = plt.subplots(figsize=(11, 3))
names = ["IDLE", "CALIB", "LAUNCH_DETECT", "ASCENT", "COAST", "APOGEE", "DESCENT", "LANDED"]
st = [names.index(r["state"]) if r["state"] in names else -1 for r in rows]
a.step(t, st, where="post")
a.set_ylim(-0.5, 10.5)
a.set_yticks(range(len(names)))
a.set_yticklabels(names)
for x, n in tr:
    a.axvline(x, color="k", lw=.5, ls=":")
    a.text(x, 7.3, f"{n} {x:.2f}s", rotation=90, fontsize=7, va="bottom")
a.set_xlabel("time since CSV t=0 (s)")
a.set_title("Firmware state per logged frame")
fig.tight_layout()
fig.savefig(os.path.join(outd, "states.png"), dpi=110)
print(tr)
