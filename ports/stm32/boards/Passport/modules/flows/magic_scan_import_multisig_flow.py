# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# magic_scan_import_multisig_flow.py - Import a multisig file

from flows import Flow


class MagicScanImportMultisigFlow(Flow):
    def __init__(self, data=None):
        super().__init__(initial_state=self.xxx, name='MagicScanImportMultisigFlow')
        self.data = data

    async def xxx(self):
        pass
