# HopeRF RFM95 / SX1276 LoRa modem, SPI4 CS PC0 (driver/lora/lora.c). Register file: first byte after CS low is
# the address (bit 7 = write), later bytes auto-increment. ID_VERSION 0x42 = 0x12. TxDone (IRQ_FLAGS 0x12 bit 3)
# reads set while the op mode is TX (mode 3); writing 1s to IRQ_FLAGS clears them.
# Airtime comes from the registers the firmware programmed (SF, BW, CR, preamble, payload length, header/CRC bits),
# using the SX1276 datasheet time-on-air formula (section 4.1.1.7). When it elapses the chip returns to STANDBY
# (mode 1) and TxDone is set, as on silicon; the firmware's TX FSM polls OPMODE until it sees STANDBY.
# MODELED SIMPLIFICATION: no RF, the packets are dropped; DIO0 is not driven (the driver polls over SPI).
import math

BW = [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000]


def airtime_s(r):
    sf = max(6, min(12, r.get(0x1E, 0x70) >> 4))
    bw = BW[min(9, r.get(0x1D, 0x72) >> 4)]
    cr = (r.get(0x1D, 0x72) >> 1) & 7
    ih = r.get(0x1D, 0) & 1
    crc = (r.get(0x1E, 0) >> 2) & 1
    ldro = (r.get(0x26, 0) >> 3) & 1
    pl = r.get(0x22, 0)
    tsym = (1 << sf) / bw
    n = 8 * pl - 4 * sf + 28 + 16 * crc - 20 * ih
    npay = 8 + max(math.ceil(n / (4 * (sf - 2 * ldro))) * (cr + 4), 0)
    npre = ((r.get(0x20, 0) << 8) | r.get(0x21, 8)) + 4.25
    return (npre + npay) * tsym


class Slave:
    def __init__(self, ctx):
        self.ctx, self.regs, self.tx_end = ctx, {0x42: 0x12}, None
        self._reset()

    def _reset(self):
        self.addr, self.write, self.n = None, False, 0

    def on_transmit(self, b):
        if self.addr is None:
            self.addr, self.write = b & 0x7F, bool(b & 0x80)
            return 0
        a = self.addr + (0 if self.addr == 0 else self.n)
        self.n += 1
        if self.write:
            if a == 0x12:
                self.regs[0x12] = self.regs.get(0x12, 0) & ~b
            else:
                self.regs[a] = b
                if a == 0x01 and (b & 7) == 3:
                    self.tx_end = self.ctx.now_ns / 1e9 + airtime_s(self.regs)
                    self.ctx.info(f't={self.ctx.now_ns/1e9:.4f} TX start mode={b:#x} airtime={airtime_s(self.regs):.4f}s ')
            return 0
        if self.tx_end is not None and self.ctx.now_ns / 1e9 >= self.tx_end:
            self.tx_end = None
            self.ctx.info(f't={self.ctx.now_ns/1e9:.4f} TX done')
            self.regs[0x01] = (self.regs[0x01] & ~7) | 1
            self.regs[0x12] = self.regs.get(0x12, 0) | 0x08
        return self.regs.get(a, 0)

    def on_finish(self):
        self._reset()
