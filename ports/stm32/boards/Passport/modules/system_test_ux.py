# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# system_test_ux.py - Self test UX


def run_system_test_ux():
    import common
    from flows import SystemTestFlow

    common.ui.create_single_card(SystemTestFlow)
    common.ui.start_card_task(card_idx=0)
