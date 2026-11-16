#!/bin/sh
# Builds the Rev 2 flight image (STM32H750VBT6, app/rev2) with arm-none-eabi-gcc and the team's own Makefile.
# Needs: git submodule update --init --recursive --depth 1   (mod, driver, lib incl. the ST HAL, emulator)
set -e
cd "$(dirname "$0")/../app/rev2"
make -j4
mkdir -p ../../sim/build
cp build/appa.elf ../../sim/build/appa.elf
arm-none-eabi-size ../../sim/build/appa.elf
