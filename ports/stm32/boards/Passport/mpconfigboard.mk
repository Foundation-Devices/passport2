# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

include $(CURDIR)/boards/$(BOARD)/bootloader/constants.mk

USE_MBOOT ?= 0

# MCU settings
MCU_SERIES = h7
CMSIS_MCU = STM32H753xx
MICROPY_FLOAT_IMPL = double
AF_FILE = boards/stm32h753_af.csv
MICROPY_PY_LVGL = 1

TEXT0_ADDR = $(BL_FW_BASE)
LD_FILES = boards/Passport/passport.ld
LDFLAGS += --defsym=BL_FW_BASE=$(BL_FW_BASE)
LDFLAGS += --defsym=BL_FW_END=$(BL_FW_END)

# MicroPython settings
MICROPY_PY_LWIP = 0
MICROPY_PY_USSL = 0
MICROPY_SSL_MBEDTLS = 0

FROZEN_MANIFEST ?= boards/Passport/manifest.py

MICROPY_EXTMOD_DIR = ../../extmod
CFLAGS_MOD += -I$(MICROPY_EXTMOD_DIR) \
  -I$(MICROPY_EXTMOD_DIR)/foundation \
  -I$(MICROPY_EXTMOD_DIR)/quirc

LV_CFLAGS += -DLV_COLOR_DEPTH=16 -DLV_COLOR_16_SWAP -DLV_TICK_CUSTOM=1

# settings that apply only to crypto C-lang code
build-Passport/boards/Passport/crypto/%.o: CFLAGS_MOD += -DRAND_PLATFORM_INDEPENDENT=1

# Bootloader CFLAGS
CFLAGS_MOD += -DBL_NVROM_BASE=$(BL_NVROM_BASE)
CFLAGS_MOD += -DBL_NVROM_SIZE=$(BL_NVROM_SIZE)
CFLAGS_MOD += -DBL_FW_HDR_BASE=$(BL_FW_HDR_BASE)
CFLAGS_MOD += -DBL_FW_BASE=$(BL_FW_BASE)

CFLAGS_MOD += -Iboards/$(BOARD)/include -Iboards/$(BOARD)/common/micro-ecc

# include code common to both the bootloader and firmware
SRC_MOD += $(addprefix boards/$(BOARD)/common/,\
                backlight.c \
                bq27520.c \
                delay.c \
                display.c \
                eeprom.c \
                gpio.c \
                i2c-init.c \
                keypad-adp-5587.c \
                pprng.c \
                ring_buffer.c \
                se.c \
                sha256.c \
                spiflash.c \
                utils.c \
                hash.c \
                micro-ecc/uECC.c)

# Customize which C source files are included here for mono vs color build
ifeq ($(SCREEN_MODE), MONO)
    SRC_MOD += $(addprefix boards/$(BOARD)/common/,\
 				lcd-sharp-ls018b7dh02.c)
    LV_CFLAGS += -DSCREEN_MODE_MONO=1
    CFLAGS += -DSCREEN_MODE_MONO=1
endif

ifeq ($(SCREEN_MODE), COLOR)
    SRC_MOD += $(addprefix boards/$(BOARD)/common/,\
				lcd-st7789.c st7789.c)
    LV_CFLAGS += -DSCREEN_MODE_COLOR=1 -DHAS_FUEL_GAUGE=1
    CFLAGS += -DSCREEN_MODE_COLOR=1 -DHAS_FUEL_GAUGE=1
endif

ifeq ($(DEV_BUILD),1)
    LV_CFLAGS += -DDEV_BUILD
endif

RUST_TARGET := thumbv7em-none-eabihf
export RUSTFLAGS := --cfg dtcm --cfg sram4
