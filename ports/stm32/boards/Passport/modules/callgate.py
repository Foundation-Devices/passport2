# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# callgate.py - Wrapper around system.dispatch() methods

from se_commands import *
import common


def fill_random(buf):
    common.system.dispatch(CMD_GET_RANDOM_BYTES, buf, 0)


def get_is_bricked():
    # see if we are a brick?
    return common.system.dispatch(CMD_IS_BRICKED, None, 0) != 0


def get_anti_phishing_words(pin_buf):
    return common.system.dispatch(CMD_GET_ANTI_PHISHING_WORDS, pin_buf, len(pin_buf))


def get_supply_chain_validation_words(buf):
    return common.system.dispatch(CMD_GET_SUPPLY_CHAIN_VALIDATION_WORDS, buf, len(buf))

# EOF
