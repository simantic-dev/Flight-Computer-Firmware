#!/bin/sh
# Builds the Rev 2 flight image (STM32H750VBT6, app/rev2) with arm-none-eabi-gcc and the team's own Makefile.
# Needs: git submodule update --init --recursive --depth 1   (mod, driver, lib incl. the ST HAL, emulator)
# Applies sim/lora-pll2.patch for the build only (see sim/README.md, "Sim-only build patch"), then reverts it.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
git apply sim/lora-pll2.patch
trap 'git -C "$ROOT" apply -R sim/lora-pll2.patch' EXIT
cd app/rev2
make -j4
mkdir -p ../../sim/build
cp build/appa.elf ../../sim/build/appa.elf
arm-none-eabi-size ../../sim/build/appa.elf
