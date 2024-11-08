# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# constants.py

from micropython import const

DEFAULT_ANIM_SPEED = const(300)

TRANSITION_DIR_REPLACE = const(0)
TRANSITION_DIR_PUSH = const(1)
TRANSITION_DIR_POP = const(2)
