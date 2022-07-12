# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# magic_scan_sign_psbt_flow.py - Import a multisig file

from flows import Flow


class MagicScanSignPsbtFlow(Flow):
    def __init__(self, data=None):
        super().__init__(initial_state=self.xxx, name='MagicScanSignPsbtFlow')
        self.data = data

    async def xxx(self):
        pass
