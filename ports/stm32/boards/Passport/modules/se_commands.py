# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# se_commands.py - Constants used to identify commands for Foundation.System.dispatch()
#
# Would be better if these were defined in Foundation.System directly using MP to export
# them. That way the constant could be shared with C, but it was not clear if that can
# be achieved in MP.

# Main commands
CMD_IS_BRICKED = const(5)
CMD_READ_SE_SLOT = const(15)
CMD_GET_ANTI_PHISHING_WORDS = const(16)
CMD_GET_RANDOM_BYTES = const(17)
CMD_PIN_CONTROL = const(18)
CMD_GET_SE_CONFIG = const(20)
CMD_GET_SUPPLY_CHAIN_VALIDATION_WORDS = const(21)

# Subcommands for CMD_PIN_CONTROL
PIN_SETUP = const(0)
PIN_ATTEMPT = const(1)
PIN_CHANGE = const(2)
PIN_GET_SECRET = const(3)
