# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# Use this to build the simulator.
#
# BUG: sometimes gets caught in a dependency loop, where it's remaking Q strings.
# - workaround: "make clean && make tool" ... just a make clean isn't enough
#
MPY_TOP = ../
PORT_TOP = $(MPY_TOP)/ports/unix
V=0
LV_CFLAGS_COLOR="-DLV_COLOR_DEPTH=16 -DHAS_FUEL_GAUGE -DSCREEN_MODE_COLOR"
LV_CFLAGS_MONO="-DLV_COLOR_DEPTH=16 -DSCREEN_MODE_MONO"
VARIANT ?= simulator
VARIANT_DIR ?= $(PWD)/variant/$(VARIANT)

# bugfix for macOS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  export PKG_CONFIG_PATH=/usr/local/opt/libffi/lib/pkgconfig
endif

MAKE_ARGS = -j 4 VARIANT=$(VARIANT) VARIANT_DIR=$(VARIANT_DIR) PROG=passport-mpy V=$(V) DEBUG=1

all:
	@echo "Run 'make mono' or 'make color'"

mono:
	cd $(PORT_TOP) && $(MAKE) $(MAKE_ARGS) SCREEN_MODE="MONO" SIM_CFLAGS="-DSCREEN_MODE_MONO=1 -DPASSPORT_SIMULATOR=1" LV_CFLAGS=$(LV_CFLAGS_MONO)

color:
	cd $(PORT_TOP) && $(MAKE) $(MAKE_ARGS) SCREEN_MODE="COLOR" SIM_CFLAGS="-DSCREEN_MODE_COLOR=1 -DPASSPORT_SIMULATOR=1" LV_CFLAGS=$(LV_CFLAGS_COLOR)

clean:
	cd $(PORT_TOP) && $(MAKE) $(MAKE_ARGS) clean
