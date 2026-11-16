#!/usr/bin/env python3
"""Decode the flight log from a flash dump (out/flash.bin) into CSV.

Layout from app/rev2/flash_appa.c (get_sensor_frame / sensor_frame_size_init):
  frame 0.. hold the preset block: byte 0 save bit, preset_data at byte 2 (96 B, CONFIG_SETTINGS at +4,
  enabled_data at preset+8). Flight frames start at frame_size * num_preset_frames.
  frame = u8 save(=1), u8 FC state, u32 ms, then by enabled_data bit:
    0 STORE_CONV      accel[3] gyro[3] mag[3] baro_pressure baro_temp        (11 f32)
    1 STORE_STATE_EST quat[4] roll_rate velo_mag velocity[3] baro_alt         (10 f32)
    2 STORE_GPS       alt_ft speed_kmh utc lon lat (5 f32) + 4 chars
    3 STORE_CANARD    feedback f32
Usage: decode_flash.py flash.bin > frames.csv
"""
import struct, sys

STATES = ["INIT", "IDLE", "CALIB", "LAUNCH_DETECT", "ASCENT", "COAST", "APOGEE", "DESCENT", "LANDED"]
COLS = (["ax", "ay", "az", "gx", "gy", "gz", "mx", "my", "mz", "baro_pres", "baro_temp"],
        ["qw", "qx", "qy", "qz", "roll_rate", "velo_mag", "vx", "vy", "vz", "baro_alt"],
        ["gps_alt_ft", "gps_speed_kmh", "gps_utc", "gps_lon", "gps_lat"],
        ["feedback"])
SIZES = (44, 40, 24, 4)


def frame_layout(enabled):
    size, cols, fmt = 6, [], "<BBI"
    for bit in range(4):
        if enabled >> bit & 1:
            size += SIZES[bit]
            cols += COLS[bit]
            fmt += "%df" % len(COLS[bit]) + ("4s" if bit == 2 else "")
            if bit == 2:
                cols += ["gps_ns", "gps_ew", "gps_gll", "gps_rmc"]
    n = 1
    s = size
    while s < 96 + 2:
        s += size
        n += 1
    return size, n, cols, fmt


def decode(blob):
    enabled = struct.unpack_from("<I", blob, 10)[0]
    size, npre, cols, fmt = frame_layout(enabled)
    rows = []
    for a in range(size * npre, len(blob) - size + 1, size):
        if blob[a] != 1:
            break
        v = list(struct.unpack_from(fmt, blob, a))
        v = [x.decode("latin1").rstrip("\0") if isinstance(x, bytes) else x for x in v]
        rows.append(v[1:])
    return enabled, size, npre, ["state", "t_ms"] + cols, rows


if __name__ == "__main__":
    blob = open(sys.argv[1], "rb").read()
    enabled, size, npre, cols, rows = decode(blob)
    print(f"# enabled_data=0x{enabled:x} frame_size={size} preset_frames={npre} frames={len(rows)}", file=sys.stderr)
    print(",".join(cols))
    for r in rows:
        print(",".join(STATES[x] if i == 0 and x < len(STATES) else str(x) for i, x in enumerate(r)))
