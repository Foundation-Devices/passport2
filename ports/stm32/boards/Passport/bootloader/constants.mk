# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

# Common bootloader file between the bootloader itself and the firmware.
#
# To get the values of some common variables/values between the firmware and
# bootloader to be used by external tools (e.g.: openocd) you can use the
# available targets here, for example, `make bl_nvrom_base SCREEN_MODE=COLOR`
#
# NOTE:
#
# On the firmware makefile you need to set V=0 in order to avoid messages by
# the MicroPython Makefiles and get the correct value without garbage.

BL_FLASH_BASE := 0x08000000

# FLASH and NVROM
#
# - FLASH is used for bootloader code and data.
# - NVROM is where the ROM secrets are stored (used to communicate with the SE).
#
# The NVROM is placed at the end of the FLASH assigned to the bootloader.
#
# NVROM is not created by the linker script, instead, after creating the binary
# we use objcopy to create a binary file which will be padded with 0x00's at the
# end until BL_NVROM_BASE to fill the "end" gap. Then, the add-secrets utility
# will append the ROM secrets if we are on a development device.
#
# The firmware is just after the BL_NVROM_BASE + BL_NVROM_SIZE
BL_NVROM_SIZE := 0x100
ifeq ($(SCREEN_MODE), MONO)
  # 0x20000 - BL_NVROM_SIZE
  BL_FLASH_SIZE  := 0x1FF00
  # BL_FLASH_BASE + BL_FLASH_SIZE
  BL_NVROM_BASE  := 0x0801FF00
  # BL_NVROM_BASE + BL_NVROM_SIZE
  BL_FW_HDR_BASE := 0x08020000
  # BL_FW_HDR_BASE + 0x800
  BL_FW_BASE     := 0x08020800
else ifeq ($(SCREEN_MODE), COLOR)
  # 0x40000 - BL_NVROM_SIZE
  BL_FLASH_SIZE  := 0x3FF00
  # BL_FLASH_BASE + BL_FLASH_SIZE
  BL_NVROM_BASE  := 0x0803FF00
  # BL_NVROM_BASE + BL_NVROM_SIZE
  BL_FW_HDR_BASE := 0x08040000
  # BL_FW_HDR_BASE + 0x800
  BL_FW_BASE     := 0x08040800
endif

# Prints the BL_FW_BASE variable to the command line
.PHONY: bl_fw_hdr_base
bl_fw_hdr_base:
	@echo $(BL_FW_HDR_BASE)

# Prints the BL_NVROM_BASE variable to the command line
.PHONY: bl_nvrom_base
bl_nvrom_base:
	@echo $(BL_NVROM_BASE)
