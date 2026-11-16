# Bosch BMM150 magnetometer, I2C2 0x10 (driver/imu/imu_legacy.c mag_init / imu_it_handler).
# CHIP_ID 0x32 at 0x40, trim registers at 0x5D.., data X/Y/Z/RHALL at 0x42..0x49.
# MODELED SIMPLIFICATION: constant raw field and trims (not a real part's, not derived from the CSV
# magnetometer columns); the flight firmware builds with nav mag_enabled = false.
import struct

TRIM = {0x5D: 0, 0x5E: 0, 0x64: 0, 0x65: 0}
for a, b in ((0x62, struct.pack("<h", 0)), (0x68, struct.pack("<h", -1000)), (0x6A, struct.pack("<H", 8000)),
             (0x6C, struct.pack("<H", 20000)), (0x6E, struct.pack("<h", -8000))):
    for i, v in enumerate(b):
        TRIM[a + i] = v
TRIM[0x70], TRIM[0x71] = 0, 30
DATA = bytes([0, 0, 0, 0, (200 << 1) & 0xFF, 200 >> 7, (7000 << 2) & 0xFF, 7000 >> 6])


class Slave:
    def __init__(self, ctx):
        self.ctx, self.ptr, self.regs = ctx, 0, {}

    def on_write(self, data):
        data = bytes(data)
        if not data:
            return
        self.ptr = data[0]
        for i, v in enumerate(data[1:]):
            self.regs[self.ptr + i] = v

    def _byte(self, a):
        if a == 0x40:
            return 0x32
        if 0x42 <= a <= 0x49:
            return DATA[a - 0x42]
        if a == 0x48 or a == 0x4A:
            return 0
        return TRIM.get(a, self.regs.get(a, 0))

    def on_read(self, count):
        return bytes(self._byte(self.ptr + i) for i in range(count))

    def on_finish(self):
        pass
