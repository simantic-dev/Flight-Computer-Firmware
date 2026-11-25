"""Animates the decoded flash log (decode_flash.py output) into results/flight.gif: what the firmware itself logged, growing in time.
usage: make_gif.py out/frames.csv out/trace.log results/flight.gif "tag"   (matplotlib, pillow)"""
import csv, re, sys, io, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
LAUNCH_S = float(os.environ.get("SDR_LAUNCH_S", "6")); LD = float(os.environ.get("SDR_FRAME0_S", "4.064"))
rows = list(csv.DictReader(l for l in open(sys.argv[1]) if not l.startswith("#")))
f = lambda k: [float(r[k]) for r in rows]
t = [float(r["t_ms"]) / 1000 + LD - LAUNCH_S for r in rows]
NAMES = {3: "LAUNCH_DETECT", 4: "ASCENT", 5: "COAST", 6: "APOGEE", 7: "DESCENT"}
tr = [(float(m[1]) - LAUNCH_S, NAMES[int(m[2], 16)]) for l in open(sys.argv[2]) for m in [re.match(r"\[([\d.]+)s\] \(TRACE\) fc_state_update .* r0=(0x\w+)", l)] if m and int(m[2], 16) >= 3]
a0 = f("baro_alt")[0]; alt = [x - a0 for x in f("baro_alt")]
series = [(alt, "baro_alt above pad, m", "C0"), (f("ax"), "accel x, m/s^2", "C1"), (f("velo_mag"), "velo_mag, m/s", "C2")]
frames = []
for k in range(1, 41):
    tc = t[0] + (t[-1] - t[0]) * k / 40; n = sum(1 for x in t if x <= tc)
    fig, ax = plt.subplots(3, 1, figsize=(7, 5), dpi=70, sharex=True)
    for a, (y, lab, c) in zip(ax, series):
        a.plot(t[:n], y[:n], c=c, lw=1); a.set_ylabel(lab, fontsize=7); a.set_xlim(t[0], t[-1]); a.set_ylim(min(y), max(y)); a.grid(alpha=.3)
        for x, nm in tr:
            if x <= tc: a.axvline(x, c="k", lw=.5, ls=":")
    for x, nm in tr:
        if x <= tc: ax[0].text(x, ax[0].get_ylim()[1], " " + nm, rotation=90, va="top", fontsize=6)
    ax[2].set_xlabel("virtual time since CSV t=0, s")
    ax[0].set_title(f"Rev 2 flight firmware on simulated H750, logged frame {n}/{len(t)}, {sys.argv[4]}", fontsize=8)
    fig.tight_layout(); bf = io.BytesIO(); fig.savefig(bf, format="png"); plt.close(fig)
    frames.append(Image.open(bf).convert("RGB").quantize(colors=64, dither=Image.Dither.NONE))
frames[0].save(sys.argv[3], save_all=True, append_images=frames[1:], duration=[120] * 39 + [1500], loop=0, optimize=True)
