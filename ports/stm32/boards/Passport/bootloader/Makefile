# SPDX-FileCopyrightText: © 2020-2022  Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# "Bootloader" Makefile
#
# Targets:
#	all - make everything, look for dafu.elf inparticular
#	clean - delete intermediates
#	clobber - delete all build products
#

include constants.mk

BOOTLOADER_VERSION = 2.1

# Toolchain
TOOLCHAIN = arm-none-eabi-
CC = $(TOOLCHAIN)gcc
OBJDUMP = $(TOOLCHAIN)objdump
OBJCOPY = $(TOOLCHAIN)objcopy
NM = $(TOOLCHAIN)nm
SIZE = $(TOOLCHAIN)size

# ports/stm32
TOP = $(realpath ../../..)
# micropython root
MPY_TOP = $(realpath $(TOP)/../..)

# Headers for ST HAL
LIB_PATH = $(MPY_TOP)/lib
HAL_DRIVERS_PATH = $(MPY_TOP)/lib/stm32lib/STM32H7xx_HAL_Driver/Src
HAL_CMSIS_PATH = $(MPY_TOP)/lib/stm32lib/CMSIS/STM32H7xx/Source/Templates
PASSPORT_PATH = ..

VPATH  = $(HAL_DRIVERS_PATH)
VPATH += $(HAL_CMSIS_PATH)
VPATH += $(HAL_CMSIS_PATH)/gcc
VPATH += $(PASSPORT_PATH)/common
VPATH += $(PASSPORT_PATH)/common/micro-ecc
VPATH += $(CURDIR)/images/$(shell echo $(SCREEN_MODE) | tr A-Z a-z)

# Basename of all targets
TARGET_NAME = bootloader-$(SCREEN_MODE)
TARGETDIR   = arm

# Source files. Important: Add them also to link-script.ld to control placement.
# Files specific to the bootloader
SOURCES  = startup_stm32h753xx.c
SOURCES += startup.c
SOURCES += main.c
SOURCES += flash.c
SOURCES += splash.c
SOURCES += update.c
SOURCES += se-atecc608a.c
SOURCES += ui.c
SOURCES += verify.c
SOURCES += version_info.c
SOURCES += sd.c
SOURCES += printf.c
SOURCES += passport_fonts.c

# Graphics
SOURCES += SPLASH.c
SOURCES += BACKGROUND.c
SOURCES += ICON_ABOUT.c
SOURCES += ICON_BACK.c
SOURCES += ICON_CANCEL.c
SOURCES += ICON_CHECKMARK.c
SOURCES += ICON_EMAIL.c
SOURCES += ICON_EXIT.c
SOURCES += ICON_FORWARD.c
SOURCES += ICON_PAGE_DOT.c
SOURCES += ICON_PAGE_DOT_SELECTED.c
SOURCES += ICON_RETRY.c
SOURCES += ICON_SHUTDOWN.c
SOURCES += LARGE_ICON_INFO.c
SOURCES += LARGE_ICON_MICROSD.c
SOURCES += LARGE_ICON_QUESTION.c
SOURCES += LARGE_ICON_ERROR.c
SOURCES += PROGRESS_CAP_LEFT.c
SOURCES += PROGRESS_CAP_RIGHT.c
SOURCES += PROGRESS_CAP_RIGHT_BG.c
SOURCES += PROGRESS_BAR_BG.c
SOURCES += PROGRESS_BAR_FG.c

# Common files between bootloader and MP
SOURCES += backlight.c
SOURCES += delay.c
SOURCES += display.c
SOURCES += gpio.c
SOURCES += hash.c

ifeq ($(SCREEN_MODE),COLOR)
SOURCES += lcd-st7789.c
SOURCES += st7789.c
SOURCES += eeprom.c
endif

ifeq ($(SCREEN_MODE),MONO)
SOURCES += lcd-sharp-ls018b7dh02.c
endif

SOURCES += pprng.c
SOURCES += se.c
SOURCES += sha256.c
SOURCES += spiflash.c
SOURCES += uECC.c
SOURCES += utils.c

SOURCES += system_stm32h7xx.c

SOURCES += stm32h7xx_hal.c
SOURCES += stm32h7xx_hal_rcc.c
SOURCES += stm32h7xx_hal_rcc_ex.c
SOURCES += stm32h7xx_hal_gpio.c
SOURCES += stm32h7xx_hal_cortex.c
SOURCES += stm32h7xx_hal_pwr.c
SOURCES += stm32h7xx_hal_pwr_ex.c
SOURCES += stm32h7xx_hal_spi.c
SOURCES += stm32h7xx_hal_dma.c

# SD Card support
SOURCES += stm32h7xx_ll_sdmmc.c
SOURCES += stm32h7xx_ll_delayblock.c
SOURCES += stm32h7xx_hal_sd.c
SOURCES += stm32h7xx_hal_sd_ex.c

# Required for LCD support
SOURCES += stm32h7xx_hal_tim.c
SOURCES += stm32h7xx_hal_tim_ex.c

# Debug console for bootloader
SOURCES += stm32h7xx_hal_uart.c
SOURCES += stm32h7xx_hal_uart_ex.c

# Files only needed for factory test bootloader build
ifeq ($(FACTORY_TEST),factory_test)
SOURCES += factory-test.c
SOURCES += stm32h7xx_hal_adc.c
SOURCES += stm32h7xx_hal_adc_ex.c
SOURCES += ../noise.c
SOURCES += ../adc.c
SOURCES += bq27520.c
endif

# Compiler flags
CFLAGS = -Wall -Werror --std=gnu99
CFLAGS += -Wno-address-of-packed-member
CFLAGS += -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
CFLAGS += -ffunction-sections -fdata-sections
CFLAGS += -mtune=cortex-m7 -mcpu=cortex-m7 -DSTM32H753xx
CFLAGS += -I. -I$(PASSPORT_PATH)/include -I$(PASSPORT_PATH)/common/micro-ecc -I$(CURDIR)/images
CFLAGS += -DPASSPORT_BOOTLOADER
CFLAGS += -DSCREEN_MODE_$(SCREEN_MODE)=1
CFLAGS += -DLV_LVGL_H_INCLUDE_SIMPLE
ifeq ($(findstring production,$(MAKECMDGOALS)),production)
CFLAGS += -DPRODUCTION_BUILD
endif
ifeq ($(findstring locked,$(MAKECMDGOALS)),locked)
CFLAGS += -DLOCKED
CFLAGS += -DPRODUCTION_BUILD
endif
#CFLAGS += -DCONVERSION_BUILD

# Flags only needed for factory test bootloader build
ifeq ($(FACTORY_TEST),factory_test)
CFLAGS += -DFACTORY_TEST
CFLAGS += -Os
else
    ifeq ($(findstring release,$(MAKECMDGOALS)),release)
        CFLAGS += -O2
    endif
endif


# Pass in the locations of stuff
CFLAGS += -DBL_FLASH_BASE=$(BL_FLASH_BASE)
CFLAGS += -DBL_FLASH_SIZE=$(BL_FLASH_SIZE)
CFLAGS += -DBL_NVROM_BASE=$(BL_NVROM_BASE)
CFLAGS += -DBL_NVROM_SIZE=$(BL_NVROM_SIZE)
CFLAGS += -DBL_FW_HDR_BASE=$(BL_FW_HDR_BASE)
CFLAGS += -DBL_FW_BASE=$(BL_FW_BASE)

ifeq ($(findstring debug,$(MAKECMDGOALS)),debug)
OBJDIR = $(TARGETDIR)/debug
CFLAGS += -g -DDEBUG
LDFLAGS += -g
else
OBJDIR = $(TARGETDIR)/release
CFLAGS += -O2
endif

# Keypad support
SOURCES += keypad-adp-5587.c

SOURCES += i2c-init.c
SOURCES += stm32h7xx_hal_i2c.c

OBJECTS = $(addprefix $(OBJDIR)/,$(SOURCES:.c=.o))

CC_SYMBOLS = -mcpu=cortex-m7

# Header file search path
INC_PATHS = $(LIB_PATH)/stm32lib/CMSIS/STM32H7xx/Include \
			$(LIB_PATH)/stm32lib/STM32H7xx_HAL_Driver/Inc \
			$(LIB_PATH)/cmsis/inc \
			$(TOP)/boards/Passport

CFLAGS += $(foreach INC,$(INC_PATHS),-I$(INC))

# Specialized linker-script here. Not the standard one!
#
LINKER_SCRIPT = link-script.ld

LDFLAGS += -flto -Wl,--gc-sections -specs=nosys.specs -specs=nano.specs -Wl,-T$(LINKER_SCRIPT)
LDFLAGS += -nostartfiles
LDFLAGS += -Wl,--defsym,BL_FLASH_BASE=$(BL_FLASH_BASE)
LDFLAGS += -Wl,--defsym,BL_FLASH_SIZE=$(BL_FLASH_SIZE)
LDFLAGS += -Wl,--defsym,BL_NVROM_BASE=$(BL_NVROM_BASE)
LDFLAGS += -Wl,--defsym,BL_NVROM_SIZE=$(BL_NVROM_SIZE)
LDFLAGS += -Wl,--defsym,BL_FW_BASE=$(BL_FW_BASE)
LDFLAGS += -Wl,-Map=$(OBJDIR)/$(TARGET_NAME).map

TARGET_ELF = $(OBJDIR)/$(TARGET_NAME).elf
TARGETS    = $(OBJDIR)/$(TARGET_NAME).bin

all: version $(TARGETS)

debug: version $(TARGETS)

locked: version $(TARGETS)

production: version $(TARGETS)

factory_test: version $(TARGETS)

# recompile on any change, because with a small project like this...
$(OBJECTS): Makefile

$(TARGETS): $(TARGET_ELF) Makefile

# link step
$(TARGET_ELF): $(OBJECTS) $(LINKER_SCRIPT) Makefile
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(TARGET_ELF) $(OBJECTS)
	$(SIZE) -Ax $@

$(OBJDIR)/%.o:  %.s
	@rm -f $@
	@[ -d $(dir $@) ] || mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

$(OBJDIR)/%.o:  %.c
	@rm -f $@
	@[ -d $(dir $@) ] || mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -MMD -MP -o $@ $<

$(OBJDIR)/%.bin: $(TARGET_ELF)
	# Use the following to build without padding to check actual BL size
	# $(OBJCOPY) -O binary  $< $@
	$(OBJCOPY) -O binary --pad-to $(BL_NVROM_BASE) --gap-fill 0x00 $< $@

ifneq ($(MAKECMDGOALS),clean)
-include $(OBJECTS:.o=.d)
endif

# make a 'release' build
release: clean all
release: CFLAGS += -DRELEASE=1 -Werror

clean:
	@$(RM) -r $(TARGETDIR)

version:
	@$(TOP)/boards/Passport/tools/version_info/version_info version_info.c $(BOOTLOADER_VERSION)
	@[ -d $(dir $(OBJDIR)/version_info.o) ] || mkdir -p $(dir $(OBJDIR)/version_info.o)
	$(CC) $(CFLAGS) -c -MMD -MP -o $(OBJDIR)/version_info.o version_info.c

.PHONY: all clean install version
.SECONDARY:
