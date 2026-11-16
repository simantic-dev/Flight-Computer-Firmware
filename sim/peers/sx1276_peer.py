# HopeRF RFM95 / SX1276 LoRa modem, SPI4 CS PC0 (driver/lora/lora.c). Register file: first byte after CS low is
# the address (bit 7 = write), later bytes auto-increment. ID_VERSION 0x42 = 0x12. TxDone (IRQ_FLAGS 0x12 bit 3)
# reads set while the op mode is TX (mode 3); writing 1s to IRQ_FLAGS clears them.
# MODELED SIMPLIFICATION: no air interface and no airtime, TX completes instantly; the packets are dropped.
class Slave:
    def __init__(self, ctx):
        self.ctx, self.regs = ctx, {0x42: 0x12}
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
            return 0
        v = self.regs.get(a, 0)
        if a == 0x12 and (self.regs.get(0x01, 0) & 7) == 3:
            v |= 0x08
        return v

    def on_finish(self):
        self._reset()
