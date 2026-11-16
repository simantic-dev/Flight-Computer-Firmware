# Bosch BMI270 IMU, I2C2 0x68 (driver/imu/imu_legacy.c). CHIP_ID 0x24; accepts the 8 KB config upload
# (INIT_CTRL 0x59 = 0 then data at 0x5E then INIT_CTRL = 1) and then reports INTERNAL_STATUS bit0 = 1.
# Serves ACC/GYR from 0x0C as int16 LE, scaled for the +-16 g / +-2000 dps ranges the firmware writes
# (main.c: IMU_ACC_RANGE_16G / IMU_GYRO_RANGE_2000; the firmware converts with 2*16*9.8/65535 m/s^2 and
# 4000/65535 dps per count). CSV accel is m/s^2, gyro dps.
# MODELED SIMPLIFICATION: no config-file semantics, no noise, data always ready.
from flightdata import FLIGHT

ACC_LSB = 2 * 16 * 9.8 / 65535
GYR_LSB = 4000 / 65535


def i16(x):
    x = max(-32768, min(32767, int(round(x))))
    return x & 0xFFFF


class Slave:
    def __init__(self, ctx):
        self.ctx, self.ptr, self.regs, self.init_bytes, self.loaded = ctx, 0, {}, 0, False

    def on_write(self, data):
        data = bytes(data)
        if not data:
            return
        self.ptr = data[0]
        body = data[1:]
        if self.ptr == 0x5E:                 # INIT_DATA burst: the address does not auto-increment
            self.init_bytes += len(body)
            return
        for i, v in enumerate(body):
            self.regs[self.ptr + i] = v
        if self.ptr == 0x59 and body:
            if body[0] == 0:
                self.init_bytes = 0
            elif body[0] == 1:
                self.loaded = True
                self.ctx.info(f"config file received: {self.init_bytes} bytes")

    def _byte(self, a):
        if a == 0x00:
            return 0x24
        if a == 0x03:
            return 0xC0                      # drdy_acc | drdy_gyr
        if a == 0x21:
            return 0x01 if self.loaded else 0x00
        if 0x0C <= a <= 0x17:
            now = self.ctx.now_ns / 1e9
            ch = (a - 0x0C) // 2
            key = ("ax", "ay", "az", "gx", "gy", "gz")[ch]
            v = FLIGHT.at(now, key) / (ACC_LSB if ch < 3 else GYR_LSB)
            r = i16(v)
            return (r >> (8 * ((a - 0x0C) % 2))) & 0xFF
        return self.regs.get(a, 0)

    def on_read(self, count):
        return bytes(self._byte(self.ptr + i) for i in range(count))

    def on_finish(self):
        pass
