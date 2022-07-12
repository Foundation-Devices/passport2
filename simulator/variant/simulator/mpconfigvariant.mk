# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

PROG ?= passport-mpy

MICROPY_PY_UASYNCIO = 1
MICROPY_PY_THREAD = 1

# TODO: make this not needed
CFLAGS_MOD += -DBL_FW_HDR_BASE=0

FROZEN_MANIFEST =
FROZEN_MPY_DIR =
