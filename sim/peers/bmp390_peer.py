# Bosch BMP390 barometer, I2C1 0x76 (driver/baro/baro.c). Register file with an 8-bit pointer.
# CHIP_ID 0x60, ERR_REG 0, STATUS drdy bits set, PRESS_DATA 0x04 (3 B) + TEMP_DATA 0x07 (3 B), NVM
# calibration from 0x31 (21 B). Raw counts come from the CSV pressure/temperature, converted with the
# firmware's own compensation formula inverted numerically (flightdata.py).
# MODELED SIMPLIFICATION: NVM coefficients are chosen, not a real part's; data is always ready.
import struct
from flightdata import FLIGHT, T1, T2, T3, P1

NVM = struct.pack("<HHbhhbbHHbbhbb", T1, T2, T3, P1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
assert len(NVM) == 21


class Slave:
    def __init__(self, ctx):
        self.ctx, self.ptr, self.regs = ctx, 0, {0x00: 0x60, 0x03: 0x70}

    def on_write(self, data):
        data = bytes(data)
        if not data:
            return
        self.ptr = data[0]
        for i, v in enumerate(data[1:]):
            self.regs[self.ptr + i] = v

    def _byte(self, a):
        if 0x31 <= a < 0x31 + 21:
            return NVM[a - 0x31]
        if 0x04 <= a <= 0x09:
            now = self.ctx.now_ns / 1e9
            r = int(FLIGHT.at(now, "rp")) if a < 7 else int(FLIGHT.at(now, "rt"))
            return (r >> (8 * ((a - 0x04) % 3))) & 0xFF
        if a == 0x02:
            return 0
        return self.regs.get(a, 0)

    def on_read(self, count):
        out = bytes(self._byte(self.ptr + i) for i in range(count))
        return out

    def on_finish(self):
        pass
