# SST25-style 4 Mbit (512 KB) SPI NOR, SPI2 CS PB12 (driver/flash/flash.c). READ 0x03, READ_HS 0x0B,
# erase 4K/32K/64K (0x20/0x52/0xD8), chip erase 0x60, byte program 0x02, AAI word program 0xAD, RDSR 0x05,
# EWSR 0x50, WRSR 0x01, WREN 0x06, WRDI 0x04, RDID 0x90, JEDEC 0x9F. Backed by a file (mmap) so the flight
# log can be decoded after the run; blank = 0xFF.
# MODELED SIMPLIFICATION: programming and erase complete instantly (BUSY never set).
import mmap, os

SIZE = 0x80000
PATH = os.environ.get("SDR_FLASH", "out/flash.bin")
os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
with open(PATH, "wb") as f:
    f.write(b"\xff" * SIZE)
MEM = mmap.mmap(os.open(PATH, os.O_RDWR), SIZE)


class Slave:
    def __init__(self, ctx):
        self.ctx, self.sr, self.wel, self.aai = ctx, 0x1C, False, False
        self._reset()

    def _reset(self):
        self.cmd, self.n, self.addr, self.pend = None, 0, 0, b""

    def _prog(self, a, v):
        if a < SIZE:
            MEM[a] &= v  # NOR programming only clears bits

    def _erase(self, size):
        a = self.addr & ~(size - 1)
        MEM[a:a + size] = b"\xff" * size

    def on_transmit(self, b):
        if self.cmd is None:
            self.cmd, self.n = b, 0
            return 0
        c, self.n = self.cmd, self.n + 1
        if c in (0x03, 0x0B):
            if self.n <= 3:
                self.addr = b if self.n == 1 else (self.addr << 8 | b)
                return 0
            if c == 0x0B and self.n == 4:
                return 0
            v = MEM[self.addr % SIZE]
            self.addr += 1
            return v
        if c == 0x05:
            return self.sr | (0x02 if self.wel else 0)
        if c == 0x9F:
            return (0xBF, 0x25, 0x8D)[min(self.n - 1, 2)]
        if c == 0x90:
            return (0, 0, 0, 0xBF, 0x8D)[min(self.n - 1, 4)] if self.n > 3 else 0
        if c in (0x20, 0x52, 0xD8, 0x02, 0xAD):
            if self.n <= 3:
                self.addr = b if self.n == 1 else (self.addr << 8 | b)
            elif c == 0x02:
                if self.wel:
                    self._prog(self.addr, b)
                    self.addr += 1
            elif c == 0xAD:
                self.pend += bytes([b])
            return 0
        if c == 0x01:
            self.sr = b & 0xBC
            return 0
        return 0

    def on_finish(self):
        c = self.cmd
        if c == 0x06:
            self.wel = True
        elif c == 0x04:
            self.wel, self.aai = False, False
        elif c == 0xAD and self.n >= 2:
            body = self.pend
            if not self.aai:
                self.aai = True
                if self.wel:
                    for i, v in enumerate(body):
                        self._prog(self.addr + i, v)
                    self.addr += len(body)
            else:
                for i, v in enumerate(body):
                    self._prog(self.addr + i, v)
                self.addr += len(body)
        elif c in (0x20, 0x52, 0xD8) and self.wel:
            self._erase({0x20: 0x1000, 0x52: 0x8000, 0xD8: 0x10000}[c])
            self.wel = False
        elif c == 0x60 and self.wel:
            MEM[:] = b"\xff" * SIZE
            self.wel = False
        elif c == 0x02 and self.wel:
            self.wel = False
        self._reset()
