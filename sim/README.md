# Simulating the Rev 2 flight computer (work in progress)

Fork-only showcase: the team's own Rev 2 flight firmware (`app/rev2`, A0002-Rev2) built unmodified except for one
labelled sim-only patch, run on the simantic `sim` with Python peers standing in for the sensors.
Upstream is SunDevilRocketry/Flight-Computer-Firmware; nothing here is sent upstream.

**Status: partial.** The firmware boots, talks to every peer, reaches IDLE and CALIB, then stops in
`error_fail_fast(0x3d)` from `telemetry_init`. No launch, ascent, apogee or descent has been simulated yet and no
flight plots exist. Nothing below claims otherwise.

## What runs

| Part | Peer | Bus | Status |
| --- | --- | --- | --- |
| BMP390 baro | `peers/bmp390_peer.py` | I2C1 0x76 | answers; pressure and temperature from the CSV, firmware compensation inverted numerically |
| BMI270 IMU | `peers/bmi270_peer.py` | I2C2 0x68 | answers; accepts the config upload, serves accel/gyro from the CSV |
| BMM150 mag | `peers/bmm150_peer.py` | I2C2 0x10 | answers; constant raw field and trims |
| SST25 4 Mbit flash | `peers/sst25_peer.py` | SPI2 CS PB12 | answers; file-backed (`out/flash.bin`) |
| RFM95 / SX1276 LoRa | `peers/sx1276_peer.py` | SPI4 CS PC0 | answers ID 0x12 and register writes; first version, see Open |
| Arm switch | `peers/arm_switch_peer.py` | PD7 | low at boot, raised at 3 s |

`flightdata.py` replays `emulator/resources/locked_in_flight.csv` (team emulator submodule, BSD-3) open loop.
Whether that CSV is a recorded flight is `unverified`.

Run: `sh sim/build.sh` then `cd sim && sim run --scenario scenario.yaml --timeout 14 --trace-symbol fc_state_update`.
`decode_flash.py` decodes the flight log from `out/flash.bin` (untested: no flight frames were written yet).

## Measured (sim 0.10.1, this scenario)

| Observation | Value |
| --- | --- |
| Boot to IDLE (`fc_state_update` r0=1) | 9.599 s virtual |
| CALIB (r0=2) | 9.803 s virtual |
| `error_fail_fast` r0=0x3d | 10.366 s virtual, immediately after a LoRa register sequence ending in a write of 0x81 to OpMode |
| SPI2 flash transactions in the first 11 s | 551 680 (boot spends most of its time reading flash) |
| Image | text 82136 B, data 8700 B, bss 6340 B |

## MODELED SIMPLIFICATIONS

- **STM32H743VG stand-in.** `sim models` has no STM32H750. H750 and H743 are the same die family; the H750 has
  less flash. Flash size, memory map and clock tree of the stand-in against the H750 are `unverified`; the image
  (82 KB) fits either. HSE is 24 MHz, the firmware's own `HSE_VALUE`.
- **Open-loop replay.** The rocket does not react to the firmware. The CSV has only ~0.7 s of pad rows, so they
  are cycled until CSV time 0 plays at sim time 8 s.
- **Peers** are register files, not the silicon: instant flash program/erase, always-ready data, chosen BMP390
  NVM coefficients, constant magnetometer field, instant LoRa TX, no noise.

## Sim-only build patch (`lora-pll2.patch`)

The SPI4 (LoRa) branch of `HAL_SPI_MspInit` calls `HAL_RCCEx_PeriphCLKConfig` with a zeroed `PLL2` struct
(M = 0), so the HAL re-enables PLL2 with DIVM2 = 0 and waits for PLL2RDY, which times out after 2 ms and ends in
`ERROR_LORA_SPI_INIT_ERROR` (0x3c) at 4.08 ms. The patch gives it the PLL2 values the SPI2 branch already uses.
Whether silicon behaves the same with DIVM2 = 0 is `unverified` (not checked against RM0433), so this is not
claimed as a model bug or as a firmware bug. `build.sh` applies the patch for the build and reverts it.

## Firmware fact: dual deploy cannot fire

`check_config_validity` in `prelaunch.c` rejects `DUAL_DEPLOY_ENABLED` and active roll / pitch-yaw control, and
arming with dual deploy calls `error_fail_fast(ERROR_CONFIG_VALIDITY_ERROR)`. So `flight_deploy` never lights an
igniter in this firmware version and APOGEE to DESCENT is the only deploy marker. This is a property of the
firmware, not of the sim.

## Open

- `telemetry_init` fails after `lora_configure`. The peer saw the ID read and a long register write sequence;
  which check in `lora_configure` returns non-OK is not yet found.
- Then: arm, calibrate, launch detect through descent, decode the flash log, plot, and measure the numbers.
- A full 196 s virtual run may exceed the 5-minute wall rule; if so it will be truncated after descent and say so.

## Licence

The firmware is BSD-3-Clause, Copyright 2025 Sun Devil Rocketry (see `LICENSE`, `NOTICE`: ST HAL BSD-3, CMSIS
Apache-2.0, ST USB SLA0044). Files under `sim/` are offered under the same BSD-3-Clause terms.
