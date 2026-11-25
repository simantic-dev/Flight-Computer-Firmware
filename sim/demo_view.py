#!/usr/bin/env python3
"""Live view of a running sim (sim/demo): follows the sim log and the file-backed SST25 flash while the sim runs.
usage: demo_view.py <sim.log> <flash.bin> <frames.txt> <sim pid>
Prints, with their original text and virtual timestamps:
  - sim --trace-symbol hits (TRACE lines), and the Python peers' own prints, verbatim
  - the firmware's debug_log messages (listed at the end, see below). Rev 2's debug_writer is a stub, so they never leave the chip; the text is
    recovered from the byte writes into debug_handle (--trace-memory) and shown as "(debug_log)".
  - the first I2C frames the sim logged (--frames), verbatim
  - flight-log frames the firmware writes to flash, decoded, every 500 ms of log time"""
import os, re, sys, time
from decode_flash import decode, STATES

log, flash, frames, pid = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
MEM = re.compile(r"\[([\d.]+)s\] \(MEM\) debug_handle write addr=0x\w+ width=1 value=0x([0-9a-f]+)")
dbg = []  # the sim only writes its --trace-memory records when the run ends
state = {"pos": 0, "text": "", "t0": None, "frames_shown": 0, "last500": -1, "nrows": 0}


def alive():
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def drain_log():
    with open(log, "rb") as f:
        f.seek(state["pos"])
        data = f.read()
    end = data.rfind(b"\n") + 1  # whole lines only
    state["pos"] += end
    for line in data[:end].decode("latin1").replace("\r", "").splitlines():
        m = MEM.match(line)
        if m:
            c = int(m[2], 16)
            if c == 10:
                if state["text"]:
                    dbg.append(f"[{state['t0']}s] (debug_log) {state['text']}")
                state["text"], state["t0"] = "", None
            elif c:
                state["t0"] = state["t0"] or m[1]
                state["text"] += chr(c)
        elif "(TRACE)" in line or line.startswith("[imu]") or line.startswith("[lora]") or line.startswith("[baro]"):
            print(line)


def drain_frames():
    if state["frames_shown"] >= 6 or not os.path.exists(frames):
        return
    with open(frames) as f:
        for i, line in enumerate(f):
            if "i2c" in line and i >= state["frames_shown"]:
                print(line.rstrip())
                state["frames_shown"] += 1
                if state["frames_shown"] >= 6:
                    break


def drain_flash(final):
    if not os.path.exists(flash):
        return
    _, _, _, cols, rows = decode(open(flash, "rb").read())
    ix = {c: i for i, c in enumerate(cols)}
    rows = rows if final else rows[:-1]  # the newest frame may be half written
    for r in rows[state["nrows"]:]:
        t = r[ix["t_ms"]]
        if t // 500 != state["last500"]:
            state["last500"] = t // 500
            print(f"(flash log) {STATES[r[0]]:<13} t={t / 1000:5.1f} s  baro_alt {r[ix['baro_alt']]:7.1f} m  pres {r[ix['baro_pres']] / 100:7.1f} hPa  "
                  f"|v| {r[ix['velo_mag']]:6.1f} m/s  ax {r[ix['ax']]:6.1f} m/s2")
    state["nrows"] = len(rows)


while True:
    running = alive()
    drain_log(); drain_frames(); drain_flash(not running)
    sys.stdout.flush()
    if not running:
        print("# debug_log messages the firmware queued (Rev 2 never transmits them; text recovered from byte writes into debug_handle):")
        print("\n".join(dbg))
        break
    time.sleep(1)
