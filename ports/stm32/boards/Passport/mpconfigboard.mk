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

FLASH_ISR_SIZE=128K
ifeq ($(SCREEN_MODE), MONO)
  # 128K reserved for nvstore
  FLASH_TEXT_SIZE=1664K
else ifeq ($(SCREEN_MODE), COLOR)
  # 128K reserved for nvstore
  FLASH_TEXT_SIZE=1662K
endif

TEXT0_ADDR = $(BL_FW_BASE)
LD_FILES = boards/Passport/passport.ld boards/common_ifs.ld
LDFLAGS += --defsym=BL_FW_BASE=$(BL_FW_BASE)
LDFLAGS += --defsym=FLASH_ISR_SIZE=$(FLASH_ISR_SIZE)
LDFLAGS += --defsym=FLASH_TEXT_SIZE=$(FLASH_TEXT_SIZE)

# MicroPython settings
MICROPY_PY_LWIP = 0
MICROPY_PY_USSL = 0
MICROPY_SSL_MBEDTLS = 0

FROZEN_MANIFEST = boards/Passport/manifest.py

MICROPY_EXTMOD_DIR = ../../extmod
CFLAGS_MOD += -I$(MICROPY_EXTMOD_DIR) \
  -I$(MICROPY_EXTMOD_DIR)/foundation \
  -I$(MICROPY_EXTMOD_DIR)/quirc \
  -I$(MICROPY_EXTMOD_DIR)/trezor-firmware/crypto \
  -I$(MICROPY_EXTMOD_DIR)/trezor-firmware/crypto/aes \
  -I$(MICROPY_EXTMOD_DIR)/trezor-firmware/crypto/chacha20poly1305 \
  -I$(MICROPY_EXTMOD_DIR)/trezor-firmware/crypto/ed25519-donna \
  -I$(MICROPY_EXTMOD_DIR)/trezor-firmware/core

CFLAGS_MOD += -DBITCOIN_ONLY=1 -DAES_128=1 -DAES_192=1

# settings that apply only to crypto C-lang code
build-Passport/boards/Passport/crypto/%.o: CFLAGS_MOD += \
	-DUSE_BIP39_CACHE=0 -DBIP32_CACHE_SIZE=0 -DUSE_BIP32_CACHE=0 -DBIP32_CACHE_MAXDEPTH=0 \
	-DRAND_PLATFORM_INDEPENDENT=1 -DUSE_BIP39_GENERATE=0 -DUSE_BIP32_25519_CURVES=0

CFLAGS_MOD += -I$(MICROPY_EXTMOD_DIR)/trezor-firmware/core/embed/extmod/modtrezorcrypto -Iboards/$(BOARD)/trezor-firmware/core

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
	CFLAGS += -DSCREEN_MODE_MONO=1
endif

ifeq ($(SCREEN_MODE), COLOR)
    SRC_MOD += $(addprefix boards/$(BOARD)/common/,\
				lcd-st7789.c st7789.c)
	CFLAGS += -DSCREEN_MODE_COLOR=1
endif
