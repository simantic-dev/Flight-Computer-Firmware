# Arm switch on PD7 (app/rev2/pindefs.h). The firmware must boot with it low (high at boot is
# error_fail_fast); raising it arms: IDLE -> CALIB -> LAUNCH_DETECT. Raised at ARM_S of virtual time.
import os

ARM_S = float(os.environ.get("SDR_ARM_S", "3.0"))


class Slave:
    def __init__(self, ctx):
        self.ctx, self.level = ctx, None
        ctx.schedule_periodic(10_000)
        self.on_timer()

    def on_gpio(self, line, level):
        pass

    def on_timer(self):
        level = self.ctx.now_us >= ARM_S * 1e6
        if level != self.level:
            self.level = level
            self.ctx.gpio(0).set(level)
