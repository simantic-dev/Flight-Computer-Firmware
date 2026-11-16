# Simulating the Rev 2 flight computer (work in progress)

Fork-only showcase: the team's own Rev 2 flight firmware (`app/rev2`, A0002-Rev2) built unmodified except for one
labelled sim-only patch, run on the simantic `sim` with Python peers standing in for the sensors.
Upstream is SunDevilRocketry/Flight-Computer-Firmware; nothing here is sent upstream.

**Status: partial.** The firmware boots (IDLE 0.92 s virtual), arms at 3 s, calibrates, initialises LoRa
without error and enters LAUNCH_DETECT at 3.56 s virtual. After about 4.06 s virtual the flight loop stops
reading sensors (cause not yet found, see Open), so no launch, ascent, apogee or descent has been simulated and no
flight plots exist. Nothing below claims otherwise.

## What runs

| Part | Peer | Bus | Status |
| --- | --- | --- | --- |
| BMP390 baro | `peers/bmp390_peer.py` | I2C1 0x76 | answers; pressure and temperature from the CSV, firmware compensation inverted numerically |
| BMI270 IMU | `peers/bmi270_peer.py` | I2C2 0x68 | answers; accepts the config upload, serves accel/gyro from the CSV |
| BMM150 mag | `peers/bmm150_peer.py` | I2C2 0x10 | answers; constant raw field and trims |
| SST25 4 Mbit flash | `peers/sst25_peer.py` | SPI2 CS PB12 | answers; file-backed (`out/flash.bin`) |
| RFM95 / SX1276 LoRa | `peers/sx1276_peer.py` | SPI4 CS PC0 | answers ID 0x12 and register writes; `lora_init` completes OK |
| Arm switch | `peers/arm_switch_peer.py` | PD7 | low at boot, raised at 3 s |

`flightdata.py` replays `emulator/resources/locked_in_flight.csv` (team emulator submodule, BSD-3) open loop.
Whether that CSV is a recorded flight is `unverified`.

Run: `sh sim/build.sh` then `cd sim && sim run --scenario scenario.yaml --timeout 14 --trace-symbol fc_state_update`.
`decode_flash.py` decodes the flight log from `out/flash.bin` (layout read from `flash_appa.c`; no real flight frames decoded yet).

## Measured (sim 0.10.1, this scenario)

| Observation | Value |
| --- | --- |
| Boot to IDLE (`fc_state_update` r0=1) | 0.925 s virtual (was 9.6 s with a blank flash) |
| CALIB (r0=2), armed at 3 s | 3.000 s virtual |
| 50 calibration samples (`sensor_dump`) | 3.41 s to 4.06 s virtual |
| LAUNCH_DETECT (r0=3) | 3.563 s virtual, `telemetry_init` returns OK |
| `sensor_dump` calls after 4.06 s | none to 6 s virtual (`unverified` why) |
| Image | text 82136 B, data 8700 B, bss 6340 B |

## Root causes found

- **0x3d (`telemetry_init` LoRa assert) was not a peer fault.** `lora_configure` returned `LORA_USING_DEFAULTS`
  (8) because the preset in RAM was all 0xFF. `lora_init` itself returns OK on every status (all HAL calls OK,
  peer sees the expected register sequence). The preset was lost in the SST25 peer: AAI word-program
  continuation frames carry no address but the peer reset its address to 0 after every frame, so the whole
  preset (and later flight frames) were programmed at address 0. Fixed in `peers/sst25_peer.py`.
- **551k SPI2 transactions** were `read_preset` scanning the whole blank 512 KB flash in 98-byte reads looking
  for a save bit. The flash now starts with a preset block (MODELED SIMPLIFICATION: stands for what the team's
  configuration tool writes; `set_default_configs` values plus WIRELESS_TRANSMISSION and a valid LoRa preset).

## MODELED SIMPLIFICATIONS

- **STM32H743VG stand-in.** `sim models` has no STM32H750. H750 and H743 are the same die family; the H750 has
  less flash. Flash size, memory map and clock tree of the stand-in against the H750 are `unverified`; the image
  (82 KB) fits either. HSE is 24 MHz, the firmware's own `HSE_VALUE`.
- **Open-loop replay.** The rocket does not react to the firmware. The CSV has only ~0.7 s of pad rows, so they
  are cycled until CSV time 0 plays at sim time 8 s.
- **Peers** are register files, not the silicon: instant flash program/erase, always-ready data, chosen BMP390
  NVM coefficients, constant magnetometer field, instant LoRa TX, no noise.

## Sim-only build patch (`lora-pll2.patch`) and the PLL2 question

The SPI4 (LoRa) branch of `HAL_SPI_MspInit` calls `HAL_RCCEx_PeriphCLKConfig` with a zero-initialised `PLL2`
struct (M = 0, N = 0). With `Spi45ClockSelection = PLL2` the HAL takes `RCCEx_PLL2_Config(..., DIVIDER_Q_UPDATE)`:
it disables PLL2 (the SPI2 branch had configured it), writes DIVM2 = 0, enables PLL2 and polls PLL2RDY for 2 ms,
returning HAL_TIMEOUT, so `error_fail_fast(ERROR_LORA_SPI_INIT_ERROR)` (0x3c) at 4.08 ms.

Evidence: RM0433 (RCC_PLLCKSELR) says DIVM2 = 0 is "prescaler disabled" and that 0 is to be used when PLL2 is
not used; the pyrite H7 RCC model (`stm32h7_rcc.rs`) implements exactly that: PLLxRDY needs PLLxON, a ready
reference and DIVMx != 0, and its PLL lock timings are from H753 bench measurements. The model follows the manual;
the sim differs from silicon only if silicon sets PLL2RDY with DIVM2 = 0, which neither the RM nor the model's
bench data supports. Verdict: a firmware configuration defect (the struct was meant to carry the SPI2 values),
expected to fail the same way on silicon. Not measured on silicon (`unverified`; no H750 rig here). The
reconfiguration would also drop the SPI2 flash clock. The patch gives the SPI4 branch the SPI2 branch's PLL2
values and is applied for the build only by `build.sh`.

## Firmware fact: dual deploy cannot fire

`check_config_validity` in `prelaunch.c` rejects `DUAL_DEPLOY_ENABLED` and active roll / pitch-yaw control, and
arming with dual deploy calls `error_fail_fast(ERROR_CONFIG_VALIDITY_ERROR)`. So `flight_deploy` never lights an
igniter in this firmware version and APOGEE to DESCENT is the only deploy marker. This is a property of the
firmware, not of the sim.

## Open

- Flight loop silent after 4.06 s virtual (LAUNCH_DETECT reached, no further `sensor_dump`). Next step: find the
  PC it waits at (candidate: the async LoRa FSM TX completion, which needs SPI4 interrupt-mode transfers and
  `lora_fsm_update` callbacks).
- Then: launch detect through descent, decode the flash log, plot. The CSV must start after LAUNCH_DETECT is
  entered (`SDR_LAUNCH_S=12`), not at 8 s.
- A full 196 s virtual run may exceed the 5-minute wall rule; if so it will be truncated after descent and say so.

## Licence

The firmware is BSD-3-Clause, Copyright 2025 Sun Devil Rocketry (see `LICENSE`, `NOTICE`: ST HAL BSD-3, CMSIS
Apache-2.0, ST USB SLA0044). Files under `sim/` are offered under the same BSD-3-Clause terms.
